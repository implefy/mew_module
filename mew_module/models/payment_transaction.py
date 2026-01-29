from odoo import models, _


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """Override to confirm orders even for pending transactions (wire transfer).

        By default, Odoo only sends quotation email for pending transactions.
        We want to confirm the order immediately when customer completes checkout,
        even if using wire transfer (pending state).
        """
        # First, handle pending transactions - confirm orders before standard processing
        for pending_tx in self.filtered(lambda tx: tx.state == 'pending'):
            # Confirm orders that are still in draft/sent state
            orders_to_confirm = pending_tx.sale_order_ids.filtered(
                lambda so: so.state in ('draft', 'sent')
            )
            for order in orders_to_confirm:
                if order._is_confirmation_amount_reached():
                    order.with_context(send_email=True).action_confirm()

        # Call standard processing
        return super()._post_process()
