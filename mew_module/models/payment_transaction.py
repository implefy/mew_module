from odoo import api, fields, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process_after_done(self):
        """Override to confirm sale order after successful payment (including partial)."""
        res = super()._post_process_after_done()

        # Confirm related sale orders
        for tx in self:
            for order in tx.sale_order_ids:
                if order.state in ('draft', 'sent'):
                    order.action_confirm()

        return res

    def action_confirm_pending(self):
        """Manually confirm a pending transaction (e.g., wire transfer received)."""
        for tx in self:
            if tx.state == 'pending':
                tx._set_done()
                tx._post_process_after_done()
