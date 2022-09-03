<template>
	<div
		v-if="step == 'Confirm Checkout' && planData"
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
			v-model="planData.title"
			readonly
		/>
		<Input
			v-if="plan"
			:label="`Credits (Minimum Credits: ${
				selectedOption == 'Annual' ? planData.amount * 12 : planData.amount
			})`"
			v-model.number="creditsToBuy"
			name="amount"
			autocomplete="off"
			type="number"
			:min="selectedOption == 'Annual' ? planData.amount * 12 : planData.amount"
		/>
		<div></div>
		<div class="text-sm">
			<p class="mb-1">
				Total Amount <span v-if="gstApplicable()">(+18% GST)</span>
			</p>
			<div class="flex rounded bg-gray-100 p-1 pl-3 font-medium">
				<strike class="mr-2" v-if="totalAmountWithoutDiscount > 0">{{
					totalAmountWithoutDiscount
				}}</strike>
				<p>{{ totalAmount }}</p>
			</div>
		</div>
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
	<div class="float-right mt-2" v-if="step == 'Confirm Checkout' && planData">
		<Button
			class="mr-2"
			v-if="this.$account.balance >= creditsToBuy"
			appearance="secondary"
			@click="useExistingCredits"
		>
			Use Existing Credits
		</Button>
		<Button
			appearance="primary"
			@click="$resources.changePlan.submit()"
			:loading="$resources.changePlan.loading"
		>
			Buy Credits
		</Button>
	</div>

	<!-- Use existing credits dialog -->
	<div v-if="step == 'Use Existing Credits'">
		<p class="text-base">
			You current credit balance is
			<span class="font-bold">{{ this.$account.balance }}</span
			>. Choosing this option will apply the existing credits to the new
			subscription. This might affect expiry of other active subscriptions. Are
			you sure you want to proceed?
		</p>
		<div class="float-right mt-2">
			<Button
				class="mr-2"
				type="secondary"
				@click="() => (this.step = 'Confirm Checkout')"
			>
				Back
			</Button>
			<Button
				appearance="primary"
				@click="$resources.changePlan.submit()"
				:loading="$resources.changePlan.loading"
			>
				Confirm
			</Button>
		</div>
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
				appearance="primary"
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
			<span class="font-semibold">** {{ this.card.last4 }}</span> to authorize
			your purchase of {{ creditsToBuy }} credits.
		</p>
		<Button
			appearance="primary"
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
</template>

<script>
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';
import { utils } from '@/utils';

export default {
	name: 'SubscriptionPlan',
	props: {
		app: null,
		site: null,
		plan: '',
		subscription: {
			default: 'new'
		}
	},
	components: {
		StripeLogo
	},
	data() {
		return {
			creditsToBuy: 0,
			totalAmount: 0,
			totalAmountWithoutDiscount: 0,
			usePartnerCredits: false,
			step: 'Confirm Checkout',
			clientSecret: null,
			paymentMethod: null,
			publishableKey: null,
			paymentOptions: ['Monthly', 'Annual'],
			selectedOption: 'Monthly',
			planData: null
		};
	},
	watch: {
		// whenever question changes, this function will run
		selectedOption(newOption, oldOption) {
			this.totalAmountWithoutDiscount = 0;
			this.creditsToBuy =
				this.planData.amount * (newOption == 'Annual' ? 12 : 1);
		},
		creditsToBuy(newAmount, oldAmount) {
			this.updateTotalAmount();
		}
	},
	methods: {
		useExistingCredits() {
			this.step = 'Use Existing Credits';
		},
		updateTotalAmount() {
			// Discount
			let amount = this.creditsToBuy;
			if (
				this.selectedOption == 'Annual' &&
				this.planData.discount_percent > 0
			) {
				this.totalAmountWithoutDiscount = this.gstApplicable()
					? Math.floor(amount + amount * 0.18)
					: this.creditsToBuy;
				this.totalAmount =
					amount - (this.planData.discount_percent / 100) * amount;
			} else {
				this.totalAmount = amount;
			}

			// GST
			if (this.gstApplicable()) {
				this.totalAmount = Math.floor(
					this.totalAmount + this.totalAmount * 0.18
				);
			} else {
				this.totalAmount = this.creditsToBuy;
			}
		},
		gstApplicable() {
			return this.$account.team.country === 'India' && this.planData.gst == 1;
		},
		async authenticateCard() {
			// Event handler to prompt a customer to authenticate a previously provided card
			this.step = 'Setting up Stripe';
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
						window.location.reload();
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
		plan() {
			return {
				method: 'press.api.marketplace.get_plan',
				params: {
					name: this.plan
				},
				auto: true,
				onSuccess(r) {
					this.planData = r;
					this.creditsToBuy = r.amount;
				}
			};
		},
		changePlan() {
			return {
				method: 'press.api.marketplace.prepaid_saas_payment',
				params: {
					name: this.subscription,
					app: this.app,
					site: this.site,
					plan: this.plan,
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
		}
	}
};
</script>
