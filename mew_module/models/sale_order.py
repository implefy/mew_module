from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_partial_payment_amount(self):
        """Get the partial payment amount from session or return full amount."""
        self.ensure_one()
        partial_amount = self.env['ir.http']._request_session().get('partial_payment_amount')
        if partial_amount and self.require_payment:
            return min(float(partial_amount), self.amount_total)
        return self.amount_total

    def _validate_partial_payment_amount(self, amount):
        """Validate that the partial payment amount is within acceptable bounds."""
        self.ensure_one()
        if amount <= 0:
            return False, 'Amount must be greater than zero'
        if amount > self.amount_total:
            return False, 'Amount cannot exceed order total'
        return True, ''
