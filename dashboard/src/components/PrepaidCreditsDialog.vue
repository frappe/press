<template>
	<Dialog
		:show="show"
		@change="$emit('update:show', $event)"
		title="Buy Credits"
	>
		<BuyPrepaidCredits
			v-if="paymentGateway === 'stripe'"
			:minimumAmount="minimumAmount"
			@success="$emit('success')"
			@cancel="$emit('update:show', false)"
		/>

		<div v-if="paymentGateway === 'razorpay'">
			<Input
				:label="`Amount (Minimum Amount: ${minimumAmount})`"
				v-model.number="creditsToBuy"
				name="amount"
				autocomplete="off"
				type="number"
				min="1"
			/>

			<div class="flex justify-between w-full mt-4">
				<Button @click="paymentGateway = null">Go Back</Button>
				<div>
					<Button
						type="primary"
						:loading="
							$resources.createRazorpayOrder.loading ||
								$resources.handlePaymentSuccess.loading
						"
						@click="buyCreditsWithRazorpay"
					>
						Buy
					</Button>
				</div>
			</div>
		</div>

		<div>
			<div v-if="!paymentGateway">
				<Button @click="paymentGateway = 'stripe'">Stripe</Button>
				<Button @click="paymentGateway = 'razorpay'">Razorpay</Button>
			</div>
		</div>
	</Dialog>
</template>
<script>
import BuyPrepaidCredits from './BuyPrepaidCredits.vue';

export default {
	name: 'PrepaidCreditsDialog',
	components: {
		BuyPrepaidCredits
	},
	data() {
		return {
			paymentGateway: null,
			creditsToBuy: 0
		};
	},
	mounted() {
		const razorpayCheckoutJS = document.createElement('script');
		razorpayCheckoutJS.setAttribute(
			'src',
			'https://checkout.razorpay.com/v1/checkout.js'
		);
		razorpayCheckoutJS.async = true;
		document.head.appendChild(razorpayCheckoutJS);
	},
	props: {
		show: {
			default: true
		},
		minimumAmount: {
			default: 0
		}
	},
	resources: {
		createRazorpayOrder() {
			return {
				method: 'press.api.billing.create_razorpay_order',
				params: {
					amount: this.creditsToBuy
				},
				onSuccess(data) {
					this.processOrder(data);
				}
			};
		},
		handlePaymentSuccess() {
			return {
				method: 'press.api.billing.handle_razorpay_payment_success',
				onSuccess() {
					this.$emit('success');
				}
			};
		},
		handlePaymentFailed() {
			return {
				method: 'press.api.billing.handle_razorpay_payment_failed',
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
				prefill: {
					email: this.$account.team.name
				},
				theme: { color: '#2490EF' },
				handler: this.handlePaymentSuccess
			};

			const rzp = new Razorpay(options);

			// Opens the payment checkout frame
			rzp.open();

			// Attach failure handler
			rzp.on('payment.failed', this.handlePaymentFailed);
		},

		handlePaymentSuccess(response) {
			this.$resources.handlePaymentSuccess.submit({ response });
		},

		handlePaymentFailed(response) {
			this.$resources.handlePaymentFailed.submit({ response });
		}
	}
};
</script>
