from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderRegisterPaymentWizard(models.TransientModel):
    _name = 'sale.order.register.payment.wizard'
    _description = 'Register Payment for Sale Order'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
    )
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.context_today,
        required=True,
    )
    payment_reference = fields.Char(
        string='Payment Reference',
        help='Reference for this payment (e.g., bank transfer reference)',
    )
    note = fields.Text(
        string='Notes',
    )

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            self.currency_id = self.order_id.currency_id
            self.amount = self.order_id.amount_remaining

    def action_register_payment(self):
        """Create a payment transaction and mark it as done."""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        if self.amount > self.order_id.amount_remaining:
            raise UserError(_('Payment amount cannot exceed the remaining amount.'))

        # Find wire transfer provider or create a manual transaction
        wire_provider = self.env['payment.provider'].search([
            ('code', '=', 'wire_transfer'),
            ('state', '=', 'enabled'),
        ], limit=1)

        if not wire_provider:
            # Fallback to any enabled provider
            wire_provider = self.env['payment.provider'].search([
                ('state', '=', 'enabled'),
            ], limit=1)

        if not wire_provider:
            raise UserError(_('No payment provider available.'))

        # Create payment transaction
        tx_values = {
            'provider_id': wire_provider.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.order_id.partner_id.id,
            'reference': self.payment_reference or f'{self.order_id.name}-{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}',
            'sale_order_ids': [(4, self.order_id.id)],
            'operation': 'offline',
        }

        tx = self.env['payment.transaction'].create(tx_values)

        # Mark as done immediately
        tx._set_done()
        tx._post_process_after_done()

        # Add note to order if provided
        if self.note:
            self.order_id.message_post(
                body=_('Payment registered: %s %s - %s') % (
                    self.amount,
                    self.currency_id.name,
                    self.note,
                ),
            )

        return {'type': 'ir.actions.act_window_close'}
