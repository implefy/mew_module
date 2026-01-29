from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.payment import PaymentPortal
from odoo.addons.sale.controllers import portal as sale_portal


class WebsiteSalePartialPay(WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        """Override to inject partial payment amount into payment form values."""
        values = super()._get_shop_payment_values(order, **kwargs)

        # Get partial amount from session
        partial_amount = request.session.get('partial_payment_amount')

        if partial_amount and order.amount_total > 0:
            partial_amount = min(float(partial_amount), order.amount_total)
            values.update({
                'partial_payment_enabled': True,
                'partial_payment_amount': partial_amount,
                'amount': partial_amount,
            })
        else:
            values.update({
                'partial_payment_enabled': True,
                'partial_payment_amount': None,
            })

        return values

    @http.route(
        '/shop/payment/partial_amount',
        type='json',
        auth='public',
        website=True,
    )
    def set_partial_payment_amount(self, amount=None, **kwargs):
        """Store the partial payment amount in session for payment processing."""
        order = request.cart
        if not order:
            return {'error': 'No order found'}

        if order.amount_total <= 0:
            return {'error': 'No amount to pay for this order'}

        if amount is None:
            # Clear partial amount, use full amount
            request.session.pop('partial_payment_amount', None)
            return {
                'success': True,
                'amount': order.amount_total,
                'message': 'Full payment selected',
            }

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return {'error': 'Invalid amount'}

        # Validate amount bounds
        min_amount = 0.01
        max_amount = order.amount_total

        if amount < min_amount:
            return {'error': f'Amount must be at least {min_amount}'}

        if amount > max_amount:
            return {'error': f'Amount cannot exceed {max_amount}'}

        # Store in session
        request.session['partial_payment_amount'] = amount

        return {
            'success': True,
            'amount': amount,
            'remaining': order.amount_total - amount,
            'message': 'Partial payment amount set',
        }

    @http.route(
        '/shop/payment/get_partial_amount',
        type='json',
        auth='public',
        website=True,
    )
    def get_partial_payment_amount(self, **kwargs):
        """Get current partial payment amount from session."""
        order = request.cart
        if not order:
            return {'error': 'No order found'}

        partial_amount = request.session.get('partial_payment_amount')

        return {
            'partial_amount': partial_amount,
            'order_total': order.amount_total,
            'partial_enabled': order.amount_total > 0,
            'currency_id': order.currency_id.id,
            'currency_symbol': order.currency_id.symbol,
        }


class PaymentPortalPartialPay(PaymentPortal):

    @http.route('/shop/payment/transaction/<int:order_id>', type='jsonrpc', auth='public', website=True)
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """Override to allow partial payment amounts."""
        from psycopg2.errors import LockNotAvailable
        from odoo.exceptions import AccessError, MissingError, UserError
        from odoo.fields import Command
        from odoo.tools import SQL

        # Check the order id and the access token
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token)
            request.env.cr.execute(
                SQL('SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE NOWAIT', order_id)
            )
        except MissingError:
            raise
        except AccessError as e:
            raise ValidationError(_("The access token is invalid.")) from e
        except LockNotAvailable:
            raise UserError(_("Payment is already being processed."))

        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been cancelled."))

        order_sudo._check_cart_is_ready_to_be_paid()

        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'partner_id': order_sudo.partner_invoice_id.id,
            'currency_id': order_sudo.currency_id.id,
            'sale_order_id': order_id,
        })

        # Handle partial payment amount
        partial_amount = request.session.get('partial_payment_amount')
        if partial_amount:
            kwargs['amount'] = min(float(partial_amount), order_sudo.amount_total)
        elif not kwargs.get('amount'):
            kwargs['amount'] = order_sudo.amount_total

        compare_amounts = order_sudo.currency_id.compare_amounts

        # Allow partial payments - only check that amount doesn't exceed total
        if compare_amounts(kwargs['amount'], order_sudo.amount_total) > 0:
            raise ValidationError(_("Payment amount cannot exceed the order total."))
        if kwargs['amount'] <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))
        if compare_amounts(order_sudo.amount_paid, order_sudo.amount_total) == 0:
            raise UserError(_("The cart has already been paid. Please refresh the page."))

        if delay_token_charge := kwargs.get('flow') == 'token':
            request.update_context(delay_token_charge=True)
        tx_sudo = self._create_transaction(
            custom_create_values={'sale_order_ids': [Command.set([order_id])]}, **kwargs,
        )

        request.session['__website_sale_last_tx_id'] = tx_sudo.id

        self._validate_transaction_for_order(tx_sudo, order_sudo)
        if delay_token_charge:
            tx_sudo._charge_with_token()

        return tx_sudo._get_processing_values()
