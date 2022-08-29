<template>
		<Dialog
			class="z-100"
			title="Checkout Details"
			v-model="showCheckoutDialog"
			@close="step = 'Confirm Checkout'"
		>
			<!--Confirm Checkout-->
			<div
				v-if="step == 'Confirm Checkout'"
				class="grid grid-cols-1 gap-2 md:grid-cols-2"
			>
				<Input
					type="select"
					:options="paymentOptions"
					label="Payment Option"
					v-model="selectedOption"
				/>
				<Input
					type="text"
					label="Selected Plan"
					v-model="this.plan.title"
					readonly
				/>
				<Input
					:label="`Credits (Minimum Credits: ${minimumAmount})`"
					v-model.number="creditsToBuy"
					name="amount"
					autocomplete="off"
					type="number"
					:min="minimumAmount"
				/>
				<Input
					type="text"
					:label="gstApplicable() ? 'Total Amount (18% GST)' : 'Total Amount'"
					v-model="totalAmount"
					readonly
				/>
			</div>
			<div hidden v-if="step == 'Confirm Checkout'">
				<Input
					class="mb-4"
					v-if="$account.team.payment_mode === 'Partner Credits'"
					type="checkbox"
					label="Use Partner Credits"
					v-model="usePartnerCredits"
				/>
			</div>
			<div class="mt-2 float-right" v-if="step == 'Confirm Checkout'">
				<Button
					type="primary"
					@click="$resources.changePlan.submit()"
					:loading="$resources.changePlan.loading"
				>
					Next
				</Button>
			</div>
			

			<!--Add Card Details, Stripe Step-->
			<div v-if="step == 'Add Card Details'" class="text-sm">Card Details</div>
			<div
				v-if="step == 'Add Card Details'"
				class="form-input my-2 block w-full py-2 pl-3"
				ref="card-element"
			></div>

			<div
				v-if="step == 'Add Card Details'"
				class="mt-2 flex w-full justify-between"
			>
				<StripeLogo />
				<div v-if="step == 'Add Card Details'">
					<Button
						@click="
							() => {
								showCheckoutDialog = false;
								step = 'Confirm Checkout';
								selectedOption = 'Monthly';
							}
						"
					>
						Cancel
					</Button>
					<Button
						class="ml-2"
						type="primary"
						@click="onBuyClick"
						:loading="paymentInProgress"
					>
						Pay
					</Button>
				</div>
			</div>


			<!-- Confirm Card Authentication -->
			<div
				v-if="step == 'Stripe Intermediate Step'"
				class="form-input sr-result requires-auth my-2 block w-full py-2 pl-3"
			>
				<p>
					Please authenticate your
					<span id="card-brand">{{ this.card.brand }}</span> card ending in
					<span class="font-semibold">** {{ this.card.last4 }}</span> to
					authorize your purchase of {{ creditsToBuy }} credits.
				</p>
				<Button
					type="primary"
					class="my-2"
					@click="authenticateCard"
					id="authenticate"
				>
					<div class="spinner hidden"></div>
					<span class="button-text">Authenticate purchase</span>
				</Button>
			</div>

			<!-- Stripe Setup Spinner -->
			<div v-if="step == 'Setting up Stripe'" class="mt-8 flex justify-center">
				<Spinner class="h-4 w-4 text-gray-600" />
			</div>

		</Dialog>
</template>

<script>
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';
import { utils } from '@/utils';

export default {
	name: 'SubscriptionPlan',
	props: { 
		subscription: {
			default: "app-subscription-frappe-00002"
		}, 
		plan: {
			default: {
				title: "Essential",
				name: "MARKETPLACE-PLAN-frappe-017",
				gst: 1
			}
		},
		minimumAmount: {
			default: 800
		}
	},
	components: {
		StripeLogo
	},
	data() {
		return {
			creditsToBuy: this.minimumAmount,
			totalAmount: 0,
			showCheckoutDialog: true,
			usePartnerCredits: false,
			step: 'Confirm Checkout',
			clientSecret: null,
			paymentMethod: null,
			publishableKey: null,
			paymentOptions: ['Monthly', 'Annual'],
			selectedOption: 'Monthly',
		};
	},
	created() {
		this.updateTotalAmount();
	},
	watch: {
    // whenever question changes, this function will run
    selectedOption(newOption, oldOption) {
			this.creditsToBuy = this.minimumAmount * (newOption == 'Annual' ? 12 : 1);
    },
		creditsToBuy(newAmount, oldAmount) {
			this.updateTotalAmount();
		}
  },	
	methods: {
		updateTotalAmount() {
			// If plan is gst inclusive add gst
			if (this.gstApplicable()) {
				this.totalAmount = Math.floor(this.creditsToBuy + this.creditsToBuy * 0.18);
			} else {
				this.totalAmount = this.creditsToBuy;
			}
		},
		gstApplicable() {
			return this.$account.team.country === 'India' && this.plan.gst
		},
		toggleCheckoutDialog() {
			this.showCheckoutDialog = true;
		},
		async authenticateCard() {
			// Event handler to prompt a customer to authenticate a previously provided card
			this.step = 'Setting up Stripe'
			this.stripe = await loadStripe(this.publishableKey);
			this.stripe
				.confirmCardPayment(this.clientSecret, {
					payment_method: this.paymentMethod
				})
				.then(function (stripeJsResult) {
					if (
						stripeJsResult.error &&
						stripeJsResult.error.code ===
							'payment_intent_authentication_failure'
					) {
						this.step = 'Add Card Details';
						this.$notify({
							title: 'Payment Error.',
							message: stripeJsResult.error,
							icon: 'X',
							color: 'red'
						});
					} else if (
						stripeJsResult.paymentIntent &&
						stripeJsResult.paymentIntent.status === 'succeeded'
					) {
						//this.showCheckoutDialog = false;
						window.location.reload()
						this.step = 'Confirm Checkout';
						this.$notify({
							title: 'Payment request received!',
							message:
								'Your plan will be change as soon as we get the payment confirmation',
							icon: 'check',
							color: 'green'
						});
					}
				});
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
				this.errorMessage = null;
				this.showCheckoutDialog = false;
				this.step = 'Confirm Checkout';
				this.$notify({
					title: 'Payment request received!',
					message:
						'Your plan will be change as soon as we get the payment confirmation',
					icon: 'check',
					color: 'green'
				});
			}
		},
		async setupStripeForCard() {
			this.step = 'Setting up Stripe';
			this.stripe = await loadStripe(this.publishableKey);
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
	},
	resources: {
		changePlan() {
			return {
				method: 'press.api.marketplace.prepaid_saas_payment',
				params: {
					name: this.subscription,
					plan: this.plan.name,
					amount: this.totalAmount,
					credits: this.creditsToBuy
				},
				async onSuccess(data) {
					let { card, payment_method, publishable_key, client_secret } = data;
					this.showCheckoutDialog = true;
					this.clientSecret = client_secret;
					this.publishableKey = publishable_key;
					if (data.error && data.error === 'authentication_required') {
						this.step = 'Stripe Intermediate Step';
						this.paymentMethod = payment_method;
						this.card = card;
					} else {
						this.setupStripeForCard();
					}
				},
				onError(e) {
					this.$notify({
						title: e,
						icon: 'x',
						color: 'red'
					});
				}
			};
		},
	}
};
</script>
