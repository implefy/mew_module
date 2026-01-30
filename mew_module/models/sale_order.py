from odoo import api, fields, models, _
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Only add amount_remaining since amount_paid already exists in Odoo
    amount_remaining = fields.Monetary(
        string='Amount Remaining',
        compute='_compute_amount_remaining',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_remaining(self):
        for order in self:
            order.amount_remaining = order.amount_total - order.amount_paid

    def _is_confirmation_amount_reached(self):
        """Override to allow any payment to confirm the order.

        By default, Odoo requires amount_paid >= prepayment_percent * amount_total.
        We override this to confirm the order when any transaction exists
        (including pending transactions like wire transfer).
        """
        self.ensure_one()
        # Check if there's any transaction with amount > 0 (any state)
        has_transaction = any(
            tx.amount > 0 for tx in self.transaction_ids
            if tx.state not in ('cancel', 'error')
        )
        return has_transaction or self.amount_paid > 0

    def _get_partial_payment_amount(self):
        """Get the partial payment amount from session or return full amount."""
        self.ensure_one()
        try:
            partial_amount = request.session.get('partial_payment_amount')
            if partial_amount and self.amount_total > 0:
                return min(float(partial_amount), self.amount_total)
        except RuntimeError:
            pass
        return self.amount_total

    def action_view_transactions(self):
        """Open the payment transactions for this order."""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('payment.action_payment_transaction')
        action['domain'] = [('sale_order_ids', 'in', self.ids)]
        action['context'] = {'default_sale_order_ids': [(6, 0, self.ids)]}
        if len(self.transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transaction_ids.id
            action['views'] = [(False, 'form')]
        return action

    def action_register_payment(self):
        """Open wizard to register a manual payment."""
        self.ensure_one()
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.register.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_amount': self.amount_remaining,
                'default_currency_id': self.currency_id.id,
            },
        }
