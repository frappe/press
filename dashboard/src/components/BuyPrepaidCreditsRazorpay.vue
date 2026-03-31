<template>
	<div>
		<p v-if="$team.doc.currency === 'INR'" class="mt-3 text-p-sm">
			If you select Razorpay, you can pay using Credit Card, Debit Card, Net
			Banking, UPI, Wallets, etc. If you are using Net Banking, it may take upto
			5 days for balance to reflect.
		</p>
		<p v-if="showPaypal" class="mt-3 text-p-sm">
			You can pay using your PayPal account. Processing may take a few minutes
			for the balance to reflect.
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
				v-if="!isPaymentComplete"
				@click="buyCreditsWithRazorpay"
			>
				Proceed to payment using {{ paypalEnabled ? 'PayPal' : 'Razorpay' }}
			</Button>
			<Button v-else variant="solid" :loading="isVerifyingPayment"
				>Confirming payment</Button
			>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';

export default {
	name: 'BuyPrepaidCreditsRazorpay',
	props: {
		amount: {
			default: 0,
		},
		minimumAmount: {
			default: 0,
		},
		isOnboarding: {
			default: false,
		},
		type: {
			type: String,
			default: 'Prepaid Credits',
		},
		paypalEnabled: {
			type: Boolean,
			default: false,
		},
	},
	data() {
		return {
			paypalEnabled: this.$team.doc.currency === 'USD' && this.paypalEnabled,
			isPaymentComplete: false,
			isVerifyingPayment: false,
		};
	},
	computed: {
		showPaypal() {
			return this.$team.doc.currency === 'USD' && this.paypalEnabled;
		},
	},
	mounted() {
		this.razorpayCheckoutJS = document.createElement('script');
		this.razorpayCheckoutJS.setAttribute(
			'src',
			'https://checkout.razorpay.com/v1/checkout.js',
		);
		this.razorpayCheckoutJS.async = true;
		document.head.appendChild(this.razorpayCheckoutJS);
	},
	resources: {
		createRazorpayOrder() {
			return {
				url: 'press.api.billing.create_razorpay_order',
				params: {
					amount: this.amount,
					transaction_type: this.type,
				},
				onSuccess(data) {
					this.processOrder(data);
				},
				validate() {
					if (this.amount < this.minimumAmount) {
						throw new DashboardError(
							'Amount less than minimum amount required',
						);
					}
				},
			};
		},
		handlePaymentFailed() {
			return {
				url: 'press.api.billing.handle_razorpay_payment_failed',
				onSuccess() {
					console.log('Payment Failed.');
				},
			};
		},
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
					email: this.$team.doc.user,
				},
				handler: this.handlePaymentSuccess,
				theme: { color: '#171717' },
				...(this.paypalEnabled
					? {
							config: {
								display: {
									blocks: {
										wallets: {
											name: 'Pay using PayPal',
											instruments: [
												{
													method: 'wallet',
													wallets: ['paypal'],
												},
											],
										},
									},
									sequence: ['block.wallets'],
									preferences: {
										show_default_blocks: false,
									},
								},
							},
						}
					: {}),
			};

			const rzp = new Razorpay(options);

			// Opens the payment checkout frame
			rzp.open();

			// Attach failure handler
			rzp.on('payment.failed', this.handlePaymentFailed);
			// rzp.on('payment.success', this.handlePaymentSuccess);
		},
		handlePaymentFailed(response) {
			this.$resources.handlePaymentFailed.submit({ response });
			toast.error('Payment failed');
		},
		handlePaymentSuccess() {
			this.isPaymentComplete = true;
			if (this.isOnboarding) {
				this.checkForOnboardingPaymentCompletion();
			} else {
				this.$emit('success');
				toast.success('Payment successful');
			}
		},
		async checkForOnboardingPaymentCompletion() {
			this.isVerifyingPayment = true;
			await this.$team.reload();
			if (!this.$team.doc.payment_mode) {
				setTimeout(this.checkForOnboardingPaymentCompletion, 2000);
			} else {
				this.isVerifyingPayment = false;
				this.$emit('success');
			}
		},
	},
	beforeUnmount() {
		this.razorpayCheckoutJS?.remove();
	},
};
</script>
