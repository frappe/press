<template>
	<div>
		<p v-if="$team.doc.currency === 'INR'" class="mt-3 text-p-sm">
			If you select Razorpay, you can pay using Credit Card, Debit Card, Net
			Banking, UPI, Wallets, etc. If you are using Net Banking, it may take upto
			5 days for balance to reflect.
		</p>
		<ErrorMessage
			class="mt-3"
			:message="$resources.createRazorpayOrder.error"
		/>
		<div class="mt-4 flex w-full justify-between">
			<div></div>
			<Button
				variant="solid"
				:loading="$resources.createRazorpayOrder.loading"
				@click="buyCreditsWithRazorpay"
			>
				Proceed to payment using Razorpay
			</Button>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';

export default {
	name: 'BuyPrepaidCreditsRazorpay',
	props: {
		amount: {
			default: 0
		},
		minimumAmount: {
			default: 0
		}
	},
	mounted() {
		this.razorpayCheckoutJS = document.createElement('script');
		this.razorpayCheckoutJS.setAttribute(
			'src',
			'https://checkout.razorpay.com/v1/checkout.js'
		);
		this.razorpayCheckoutJS.async = true;
		document.head.appendChild(this.razorpayCheckoutJS);
	},
	resources: {
		createRazorpayOrder() {
			return {
				url: 'press.api.billing.create_razorpay_order',
				params: {
					amount: this.amount
				},
				onSuccess(data) {
					this.processOrder(data);
				},
				validate() {
					if (this.amount < this.minimumAmount) {
						return 'Amount less than minimum amount required';
					}
				}
			};
		},
		handlePaymentFailed() {
			return {
				url: 'press.api.billing.handle_razorpay_payment_failed',
				onSuccess() {
					console.log('Payment Failed.');
				}
			};
		}
	},
	methods: {
		buyCreditsWithRazorpay() {
			this.$resources.createRazorpayOrder.submit();
		},
		processOrder(data) {
			const options = {
				key: data.key_id,
				order_id: data.order_id,
				name: 'Frappe Cloud',
				image: '/assets/press/images/frappe-cloud-logo.png',
				prefill: {
					email: this.$team.doc.user
				},
				theme: { color: '#171717' },
				handler: () => {
					this.$emit('success');
				}
			};

			const rzp = new Razorpay(options);

			// Opens the payment checkout frame
			rzp.open();

			// Attach failure handler
			rzp.on('payment.failed', this.handlePaymentFailed);
			rzp.on('payment.success', this.handlePaymentSuccess);
		},
		handlePaymentFailed(response) {
			this.$resources.handlePaymentFailed.submit({ response });
			toast.error('Payment failed');
		},
		handlePaymentSuccess(response) {
			toast.success('Payment successful');
		}
	},
	beforeUnmount() {
		this.razorpayCheckoutJS?.remove();
	}
};
</script>
