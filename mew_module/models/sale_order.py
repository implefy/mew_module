from odoo import api, fields, models
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_partial_payment_amount(self):
        """Get the partial payment amount from session or return full amount."""
        self.ensure_one()
        try:
            partial_amount = request.session.get('partial_payment_amount')
            if partial_amount and self.amount_total > 0:
                return min(float(partial_amount), self.amount_total)
        except RuntimeError:
            # No request context available (e.g., in cron jobs)
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
        # If there's a partial payment in session, consider the order payable
        try:
            partial_amount = request.session.get('partial_payment_amount')
            if partial_amount:
                return True
        except RuntimeError:
            pass
        return super()._has_to_be_paid()
