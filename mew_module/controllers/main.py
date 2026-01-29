from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSalePartialPay(WebsiteSale):

    @http.route()
    def shop_payment(self, **post):
        """Override to add partial payment context to payment page."""
        response = super().shop_payment(**post)

        order = request.website.sale_get_order()
        if order and order.require_payment:
            # Add partial payment data to qcontext
            if hasattr(response, 'qcontext'):
                response.qcontext.update({
                    'partial_payment_enabled': True,
                    'order_amount_total': order.amount_total,
                    'order_amount_paid': order.amount_paid if hasattr(order, 'amount_paid') else 0.0,
                    'order_amount_residual': order.amount_total - (order.amount_paid if hasattr(order, 'amount_paid') else 0.0),
                    'currency': order.currency_id,
                })

        return response

    @http.route(
        '/shop/payment/partial_amount',
        type='json',
        auth='public',
        website=True,
    )
    def set_partial_payment_amount(self, amount=None, **kwargs):
        """Store the partial payment amount in session for payment processing."""
        order = request.website.sale_get_order()
        if not order:
            return {'error': 'No order found'}

        if not order.require_payment:
            return {'error': 'Partial payment not enabled for this order'}

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
        order = request.website.sale_get_order()
        if not order:
            return {'error': 'No order found'}

        partial_amount = request.session.get('partial_payment_amount')

        return {
            'partial_amount': partial_amount,
            'order_total': order.amount_total,
            'partial_enabled': order.require_payment,
            'currency_id': order.currency_id.id,
            'currency_symbol': order.currency_id.symbol,
        }
