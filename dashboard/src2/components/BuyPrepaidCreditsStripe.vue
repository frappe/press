<template>
	<div>
		<label
			class="block"
			:class="{
				'pointer-events-none h-0.5 opacity-0': step != 'Add Card Details',
				'mt-4': step == 'Add Card Details'
			}"
		>
			<span class="text-sm leading-4 text-gray-700">
				Credit or Debit Card
			</span>
			<div class="form-input mt-2 block w-full pl-3" ref="card-element"></div>
			<ErrorMessage class="mt-1" :message="cardErrorMessage" />
		</label>

		<div v-if="step == 'Setting up Stripe'" class="mt-8 flex justify-center">
			<Spinner class="h-4 w-4 text-gray-600" />
		</div>
		<ErrorMessage
			class="mt-2"
			:message="$resources.createPaymentIntent.error || errorMessage"
		/>
		<div class="mt-4 flex w-full justify-between">
			<div></div>
			<div v-if="step == 'Get Amount'">
				<Button
					variant="solid"
					@click="$resources.createPaymentIntent.submit()"
					:loading="$resources.createPaymentIntent.loading"
				>
					Proceed to payment using Stripe
				</Button>
			</div>
			<div v-if="step == 'Add Card Details'">
				<Button
					class="ml-2"
					variant="solid"
					@click="onBuyClick"
					:loading="paymentInProgress"
				>
					Make payment via Stripe
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';

export default {
	name: 'BuyPrepaidCreditsStripe',
	components: {
		StripeLogo
	},
	props: {
		amount: {
			default: 0
		},
		minimumAmount: {
			default: 0
		}
	},
	data() {
		return {
			step: 'Get Amount', // Get Amount / Add Card Details
			clientSecret: null,
			cardErrorMessage: null,
			errorMessage: null,
			paymentInProgress: false
		};
	},
	resources: {
		createPaymentIntent() {
			return {
				url: 'press.api.billing.create_payment_intent_for_buying_credits',
				params: {
					amount: this.amount
				},
				validate() {
					if (this.amount < this.minimumAmount) {
						return `Amount must be greater than ${this.minimumAmount}`;
					}
				},
				async onSuccess(data) {
					this.step = 'Setting up Stripe';
					let { publishable_key, client_secret } = data;
					this.clientSecret = client_secret;
					this.stripe = await loadStripe(publishable_key);
					this.elements = this.stripe.elements();
					let theme = this.$theme;
					let style = {
						base: {
							color: theme.colors.black,
							fontFamily: theme.fontFamily.sans.join(', '),
							fontSmoothing: 'antialiased',
							fontSize: '13px',
							'::placeholder': {
								color: theme.colors.gray['400']
							}
						},
						invalid: {
							color: theme.colors.red['600'],
							iconColor: theme.colors.red['600']
						}
					};
					this.card = this.elements.create('card', {
						hidePostalCode: true,
						style: style,
						classes: {
							complete: '',
							focus: 'bg-gray-100'
						}
					});

					this.step = 'Add Card Details';
					this.$nextTick(() => {
						this.card.mount(this.$refs['card-element']);
					});

					this.card.addEventListener('change', event => {
						this.cardErrorMessage = event.error?.message || null;
					});
					this.card.addEventListener('ready', () => {
						this.ready = true;
					});
				}
			};
		}
	},
	methods: {
		setupStripe() {
			this.$resources.createPaymentIntent.submit();
		},
		async onBuyClick() {
			this.paymentInProgress = true;
			let payload = await this.stripe.confirmCardPayment(this.clientSecret, {
				payment_method: {
					card: this.card
				}
			});

			this.paymentInProgress = false;
			if (payload.error) {
				this.errorMessage = payload.error.message;
			} else {
				this.$emit('success');
				this.errorMessage = null;
			}
		}
	},
	computed: {
		totalAmount() {
			let { currency, billing_info } = this.$account
				? this.$account.team
				: this.$team.doc;
			if (currency === 'INR') {
				return Number(
					(
						this.amount +
						this.amount * (billing_info.gst_percentage || 0)
					).toFixed(2)
				);
			} else {
				return this.amount;
			}
		}
	}
};
</script>
