from odoo import api, fields, models, _
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Payment tracking fields
    amount_paid = fields.Monetary(
        string='Amount Paid',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_remaining = fields.Monetary(
        string='Amount Remaining',
        compute='_compute_payment_amounts',
        store=True,
        currency_field='currency_id',
    )
    payment_transaction_ids = fields.One2many(
        'payment.transaction',
        'sale_order_ids',
        string='Payment Transactions',
    )
    payment_transaction_count = fields.Integer(
        string='Transaction Count',
        compute='_compute_payment_transaction_count',
    )

    @api.depends('transaction_ids.state', 'transaction_ids.amount', 'amount_total')
    def _compute_payment_amounts(self):
        for order in self:
            paid = sum(
                tx.amount for tx in order.transaction_ids
                if tx.state in ('done', 'authorized')
            )
            order.amount_paid = paid
            order.amount_remaining = order.amount_total - paid

    @api.depends('transaction_ids')
    def _compute_payment_transaction_count(self):
        for order in self:
            order.payment_transaction_count = len(order.transaction_ids)

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

    def _validate_partial_payment_amount(self, amount):
        """Validate that the partial payment amount is within acceptable bounds."""
        self.ensure_one()
        if amount <= 0:
            return False, 'Amount must be greater than zero'
        if amount > self.amount_total:
            return False, 'Amount cannot exceed order total'
        return True, ''

    def _has_to_be_paid(self):
        """Override to allow confirmation with partial payments."""
        self.ensure_one()
        try:
            partial_amount = request.session.get('partial_payment_amount')
            if partial_amount:
                return True
        except RuntimeError:
            pass
        return super()._has_to_be_paid()

    def action_view_transactions(self):
        """Open the payment transactions for this order."""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('payment.action_payment_transaction')
        action['domain'] = [('sale_order_ids', 'in', self.ids)]
        action['context'] = {'default_sale_order_ids': [(6, 0, self.ids)]}
        if self.payment_transaction_count == 1:
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
