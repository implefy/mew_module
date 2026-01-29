/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.PartialPaymentWidget = publicWidget.Widget.extend({
    selector: '#partial_payment_section',
    events: {
        'change input[name="payment_type"]': '_onPaymentTypeChange',
        'input #partial_amount_input': '_onAmountInput',
        'change #partial_amount_input': '_onAmountChange',
    },

    start() {
        this._super(...arguments);
        this.$fullPayment = this.$('#full_payment');
        this.$partialPayment = this.$('#partial_payment');
        this.$amountWrapper = this.$('#partial_amount_wrapper');
        this.$amountInput = this.$('#partial_amount_input');
        this.$remainingDiv = this.$('#partial_remaining');
        this.$remainingAmount = this.$('#remaining_amount');
        this.$errorDiv = this.$('#partial_error');
        this.maxAmount = parseFloat(this.$amountInput.data('max')) || 0;
        this.currencyId = this.$amountInput.data('currency');
    },

    _onPaymentTypeChange(ev) {
        const isPartial = ev.target.value === 'partial';
        this.$amountWrapper.toggle(isPartial);

        if (!isPartial) {
            // Reset to full payment
            this._setPartialAmount(null);
            this.$amountInput.val('');
            this.$remainingDiv.hide();
            this.$errorDiv.hide();
        } else {
            this.$amountInput.focus();
        }
    },

    _onAmountInput(ev) {
        const amount = parseFloat(ev.target.value) || 0;
        this._validateAndShowRemaining(amount);
    },

    _onAmountChange(ev) {
        const amount = parseFloat(ev.target.value) || 0;
        if (this._validateAmount(amount)) {
            this._setPartialAmount(amount);
        }
    },

    _validateAmount(amount) {
        this.$errorDiv.hide();

        if (amount <= 0) {
            this.$errorDiv.text('Please enter a valid amount').show();
            return false;
        }

        if (amount > this.maxAmount) {
            this.$errorDiv.text(`Amount cannot exceed ${this.maxAmount}`).show();
            return false;
        }

        return true;
    },

    _validateAndShowRemaining(amount) {
        if (amount > 0 && amount <= this.maxAmount) {
            const remaining = this.maxAmount - amount;
            this.$remainingAmount.text(remaining.toFixed(2));
            this.$remainingDiv.show();
            this.$errorDiv.hide();
        } else {
            this.$remainingDiv.hide();
            if (amount > this.maxAmount) {
                this.$errorDiv.text(`Amount cannot exceed ${this.maxAmount}`).show();
            }
        }
    },

    async _setPartialAmount(amount) {
        try {
            const result = await rpc('/shop/payment/partial_amount', {
                amount: amount,
            });

            if (result.error) {
                this.$errorDiv.text(result.error).show();
            } else {
                // Trigger event for payment form to update
                this.trigger_up('partial_amount_changed', {
                    amount: result.amount,
                    remaining: result.remaining || 0,
                });
            }
        } catch (error) {
            console.error('Failed to set partial payment amount:', error);
            this.$errorDiv.text('Failed to update payment amount').show();
        }
    },
});

export default publicWidget.registry.PartialPaymentWidget;
