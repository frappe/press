<template>
	<Dialog
		:modelValue="modelValue"
		@update:modelValue="$emit('update:modelValue', $event)"
		title="Buy Credits"
		:subtitle="paymentGateway ? '' : 'Choose your payment gateway'"
	>
		<BuyPrepaidCredits
			v-if="paymentGateway === 'stripe'"
			:minimumAmount="minimumAmount"
			@success="$emit('success')"
			@cancel="$emit('update:modelValue', false)"
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

			<p class="mt-3 text-xs">
				<span class="font-semibold">Note</span>: If you are using Net Banking,
				it may take upto 5 days for balance to reflect.
			</p>

			<ErrorMessage
				class="mt-3"
				:error="$resources.createRazorpayOrder.error"
			/>

			<div class="mt-4 flex w-full justify-between">
				<Button @click="paymentGateway = null">Go Back</Button>
				<div>
					<Button
						type="primary"
						:loading="$resources.createRazorpayOrder.loading"
						@click="buyCreditsWithRazorpay"
					>
						Buy
					</Button>
				</div>
			</div>
		</div>

		<div>
			<div v-if="!paymentGateway" class="grid grid-cols-1 gap-2 sm:grid-cols-2">
				<Button
					v-if="
						$account.team.currency === 'INR' || $account.team.razorpay_enabled
					"
					@click="paymentGateway = 'razorpay'"
					class="py-2"
				>
					<img class="w-24" src="../assets/razorpay.svg" alt="Razorpay Logo" />
				</Button>
				<Button @click="paymentGateway = 'stripe'">
					<img class="h-7 w-24" src="../assets/stripe.svg" alt="Stripe Logo" />
				</Button>
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

		if (
			this.$account.team.currency === 'USD' &&
			!this.$account.team.razorpay_enabled
		) {
			this.paymentGateway = 'stripe';
		}
	},
	props: {
		modelValue: {
			default: true
		},
		minimumAmount: {
			type: Number,
			default: 0
		}
	},
	emits: ['update:modelValue', 'success'],
	resources: {
		createRazorpayOrder() {
			return {
				method: 'press.api.billing.create_razorpay_order',
				params: {
					amount: this.creditsToBuy
				},
				onSuccess(data) {
					this.processOrder(data);
				},
				validate() {
					if (this.creditsToBuy < this.minimumAmount) {
						return 'Amount less than minimum amount required';
					}
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
				name: 'Frappe Cloud',
				image: '/assets/press/images/frappe-cloud-logo.png',
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
			this.$emit('success');
		},

		handlePaymentFailed(response) {
			this.$resources.handlePaymentFailed.submit({ response });
		}
	},
	watch: {
		minimumAmount(amt) {
			console.log(amt);
		}
	}
};
</script>
