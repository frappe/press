<template>
	<div class="upi-autopay-form">
		<p class="mb-6 text-p-base text-gray-700">
			Simplify your billing by authorizing
			<strong>recurring monthly payments</strong> for your Frappe Cloud invoices
			via Razorpay. Once set up, we’ll handle your future invoices
			automatically—no manual intervention required.
		</p>
		<FormControl
			label="Monthly Autopay Limit"
			type="number"
			v-model="maxAmount"
			:min="500"
			:max="100000"
			placeholder="50000"
		/>
		<div class="mt-2 text-p-sm text-gray-600">
			<div class="font-medium">Range: ₹500 - ₹1,00,000</div>

			<div class="mt-2 text-gray-500 italic">
				<strong>Important:</strong> If an invoice exceeds this limit, the
				auto-debit will fail. Set this slightly higher than your typical bill to
				ensure uninterrupted service.
			</div>
		</div>
		<ErrorMessage
			class="mt-3"
			:message="$resources.createRazorpayMandate.error"
		/>
		<Button
			class="mt-4"
			variant="solid"
			:loading="
				$resources.createRazorpayMandate.loading ||
				$resources.handleMandateSuccess.loading
			"
			@click="setupAutopay"
		>
			Enable Monthly Autopay
		</Button>
	</div>
</template>

<script>
import { FormControl, Button, ErrorMessage } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { loadRazorpayScript } from '../../utils/razorpay';

export default {
	name: 'UPIAutopayForm',
	props: {
		isBackground: Boolean,
		passedAmount: Number,
	},
	emits: ['success', 'initiate', 'cancel', 'opened'],
	components: {
		FormControl,
		Button,
		ErrorMessage,
	},
	data() {
		return {
			maxAmount: this.passedAmount || null,
			pendingMandateName: '',
		};
	},
	mounted() {
		loadRazorpayScript();
		if (this.isBackground) {
			this.$resources.createRazorpayMandate.submit();
		}
	},
	resources: {
		createRazorpayMandate() {
			return {
				url: 'press.api.billing.create_razorpay_mandate',
				params: {
					max_amount: this.maxAmount,
					auth_type: 'upi',
				},
				onSuccess(data) {
					this.pendingMandateName = data.mandate_name;
					this.openRazorpayCheckout(data);
				},
				onError(error) {
					toast.error(error.messages?.[0] || 'Failed to create mandate');
				},
			};
		},
		handleMandateSuccess() {
			return {
				url: 'press.api.billing.handle_razorpay_mandate_success',
				onSuccess() {
					toast.success('UPI Autopay authorized successfully!');
					this.$emit('success');
				},
				onError(error) {
					toast.error(error.messages?.[0] || 'Failed to verify authorization');
				},
			};
		},
		cancelMandate() {
			return {
				url: 'press.api.billing.cancel_razorpay_mandate',
				onSuccess() {
					this.$emit('cancel');
				},
			};
		},
	},
	methods: {
		setupAutopay() {
			if (!this.maxAmount || this.maxAmount < 500) {
				toast.error('Maximum amount must be at least ₹500');
				return;
			}
			if (this.maxAmount > 100000) {
				toast.error('Maximum amount cannot exceed ₹1,00,000');
				return;
			}
			this.$emit('initiate', this.maxAmount);
			// this.$resources.createRazorpayMandate.submit();
		},

		async openRazorpayCheckout(orderData) {
			await loadRazorpayScript();
			const options = {
				key: orderData.key_id,
				order_id: orderData.order_id,
				customer_id: orderData.customer_id,
				recurring: '1',
				name: 'Frappe Cloud',
				description: 'UPI Autopay Authorization',
				handler: (response) => {
					// Keep razorpay-open until API call completes — removing it here
					// would show the dialog overlay, which gets an accidental outside
					// click from Razorpay's iframe removal and closes the dialog before
					// the success emit fires.
					this.handlePaymentSuccess(response);
				},
				modal: {
					ondismiss: () => {
						toast.info('Authorization cancelled');
						this.$resources.cancelMandate.submit({
							mandate_name: this.pendingMandateName,
						});
					},
				},
				theme: {
					color: '#171717',
				},
			};

			const rzp = new window.Razorpay(options);
			rzp.on('payment.failed', (response) => {
				this.handlePaymentFailure(response);
			});
			rzp.open();
			this.$emit('opened');
		},

		handlePaymentSuccess(response) {
			const loadingToast = toast.loading('Verifying authorization...');
			this.$resources.handleMandateSuccess
				.submit({
					razorpay_payment_id: response.razorpay_payment_id,
					razorpay_order_id: response.razorpay_order_id,
					razorpay_signature: response.razorpay_signature,
					mandate_name: this.pendingMandateName,
				})
				.finally(() => {
					toast.dismiss(loadingToast);
				});
		},

		handlePaymentFailure(response) {
			const error = response.error;
			toast.error(error.description || 'Authorization failed');
		},
	},
};
</script>
