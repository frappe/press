<template>
	<div class="upi-autopay-form">
		<p class="mb-4 text-p-base text-gray-700">
			UPI Autopay allows automatic payments for your Frappe Cloud invoices.
			You'll authorize via Razorpay Checkout.
		</p>
		<FormControl
			label="Maximum Amount (INR)"
			type="number"
			v-model="maxAmount"
			:min="1000"
			:max="100000"
			placeholder="50000"
		/>
		<p class="mt-2 text-p-sm text-gray-600">
			This is the maximum amount that can be auto-debited per transaction.
			Recommended: Set higher than your typical monthly invoice.
		</p>
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
			Setup UPI Autopay
		</Button>
	</div>
</template>

<script>
import { FormControl, Button, ErrorMessage } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'UPIAutopayForm',
	emits: ['success'],
	components: {
		FormControl,
		Button,
		ErrorMessage,
	},
	data() {
		return {
			maxAmount: 50000,
			pendingMandateName: '',
		};
	},
	mounted() {
		this.loadRazorpayScript();
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
	},
	methods: {
		loadRazorpayScript() {
			if (window.Razorpay) return;
			const script = document.createElement('script');
			script.src = 'https://checkout.razorpay.com/v1/checkout.js';
			script.async = true;
			document.head.appendChild(script);
		},

		setupAutopay() {
			if (!this.maxAmount || this.maxAmount < 100) {
				toast.error('Maximum amount must be at least ₹100');
				return;
			}
			this.$resources.createRazorpayMandate.submit();
		},

		openRazorpayCheckout(orderData) {
			const options = {
				key: orderData.key_id,
				order_id: orderData.order_id,
				customer_id: orderData.customer_id,
				recurring: '1',
				name: 'Frappe Cloud',
				description: 'UPI Autopay Authorization',
				handler: (response) => {
					this.handlePaymentSuccess(response);
				},
				modal: {
					ondismiss: () => {
						toast.info('Authorization cancelled');
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
		},

		handlePaymentSuccess(response) {
			this.$resources.handleMandateSuccess.submit({
				razorpay_payment_id: response.razorpay_payment_id,
				razorpay_order_id: response.razorpay_order_id,
				razorpay_signature: response.razorpay_signature,
				mandate_name: this.pendingMandateName,
			});
		},

		handlePaymentFailure(response) {
			const error = response.error;
			toast.error(error.description || 'Authorization failed');
		},
	},
};
</script>
