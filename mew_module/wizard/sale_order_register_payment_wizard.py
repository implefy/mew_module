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
    pending_transaction_id = fields.Many2one(
        'payment.transaction',
        string='Pending Transaction',
        compute='_compute_pending_transaction',
    )

    @api.depends('order_id')
    def _compute_pending_transaction(self):
        for wizard in self:
            # Find pending transaction for this order (e.g., wire transfer waiting for confirmation)
            pending_tx = wizard.order_id.transaction_ids.filtered(
                lambda tx: tx.state == 'pending'
            )
            wizard.pending_transaction_id = pending_tx[:1] if pending_tx else False

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            self.currency_id = self.order_id.currency_id
            self.amount = self.order_id.amount_remaining

    def action_register_payment(self):
        """Confirm pending transaction or create new one and mark as done."""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        if self.amount > self.order_id.amount_remaining:
            raise UserError(_('Payment amount cannot exceed the remaining amount (%(remaining)s).',
                            remaining=self.order_id.amount_remaining))

        # Check if there's a pending transaction to confirm
        pending_tx = self.order_id.transaction_ids.filtered(lambda tx: tx.state == 'pending')

        if pending_tx:
            # Confirm the existing pending transaction
            tx = pending_tx[0]
            if self.amount != tx.amount:
                # Update amount if different
                tx.amount = self.amount
            tx._set_done(state_message=_('Payment confirmed manually on %s. Reference: %s') % (
                self.payment_date, self.payment_reference or 'N/A'
            ))
        else:
            # Create a new transaction for manual payment
            wire_provider = self.env['payment.provider'].search([
                ('code', '=', 'wire_transfer'),
                ('state', 'in', ['enabled', 'test']),
                ('company_id', '=', self.order_id.company_id.id),
            ], limit=1)

            if not wire_provider:
                wire_provider = self.env['payment.provider'].search([
                    ('state', 'in', ['enabled', 'test']),
                    ('company_id', '=', self.order_id.company_id.id),
                ], limit=1)

            if not wire_provider:
                raise UserError(_('No payment provider available. Please configure a payment provider.'))

            reference = self.payment_reference or f'{self.order_id.name}-MANUAL-{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}'

            tx = self.env['payment.transaction'].create({
                'provider_id': wire_provider.id,
                'amount': self.amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.order_id.partner_id.id,
                'reference': reference,
                'sale_order_ids': [(4, self.order_id.id)],
                'operation': 'offline',
            })

            tx._set_done(state_message=_('Manual payment registered on %s.') % self.payment_date)

        # Let Odoo's standard _post_process handle order confirmation and invoicing
        tx._post_process()

        # Add note to order if provided
        if self.note:
            self.order_id.message_post(
                body=_('Payment of %(amount)s %(currency)s registered. %(note)s',
                       amount=self.amount,
                       currency=self.currency_id.name,
                       note=self.note),
            )

        return {'type': 'ir.actions.act_window_close'}
