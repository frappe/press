<template>
	<div v-if="step == 'Confirm Checkout'" class="flex-row text-sm">
		<div class="flex justify-between mb-4">
			<p class="my-auto">Billing</p>
			<Input type="select" :options="paymentOptions" v-model="selectedOption" />
		</div>

		<table v-if="$account.team" class="text w-full text-sm">
			<thead>
				<tr class="text-gray-600">
					<th class="border-b text-left font-normal">App</th>
					<th
						class="whitespace-nowrap border-b py-2 pr-2 text-center font-normal"
					>
						Plan
					</th>
					<th class="border-b py-3 pr-2 text-right font-normal">
						Amount /month
					</th>
				</tr>
			</thead>
			<tbody>
				<!--Change Plan-->
				<tr
					v-if="renewal && $resources.subscriptions.data"
					v-for="(row, i) in $resources.subscriptions.data"
					:key="row.idx"
				>
					<td class="border-b border-r">
						<ListItem :title="row.app" :subtitle="row.site" />
					</td>
					<td class="border-b border-r text-center">
						<p class="text-base self-center">{{ row.selected_plan.plan }}</p>
					</td>
					<td class="border-b text-right font-semibold">
						<p class="text-base self-center">
							{{ row.selected_plan.amount }}
						</p>
					</td>
				</tr>

				<!--Renew Subscriptions-->
				<tr v-if="!renewal && planData">
					<td class="border-b border-r">
						<ListItem :title="app" :subtitle="site" />
					</td>
					<td class="border-b border-r text-center">
						<p class="text-base self-center">{{ planData.title }}</p>
					</td>
					<td class="border-b text-right font-semibold">
						<p class="text-base self-center">
							{{ planData.amount }}
						</p>
					</td>
				</tr>
			</tbody>
		</table>

		<div class="flex-row mt-4" v-if="$account.team">
			<div class="flex justify-between mb-3">
				<p>Subtotal</p>
				<p class="text-lg">
					{{ subtotal }}
				</p>
			</div>

			<div class="flex justify-between mb-3">
				<p>Discount</p>
				<p class="text-green-500 text-lg">
					{{ discount_percent == 0 ? '-' : discount_percent + '%' }}
				</p>
			</div>

			<div class="flex justify-between">
				GST (if applicable)
				<p class="text-red-500 text-lg">18%</p>
			</div>

			<hr class="my-4" />
			<div class="flex justify-between">
				<p class="mb-3">Allocated Credits</p>
				<p class="text-lg">
					{{ creditsToBuy }}
				</p>
			</div>
			<div
				class="flex justify-between"
				v-if="$resources.subscriptions.data || planData"
			>
				<p class="mb-3 font-medium">Total</p>
				<p class="text-xl font-semibold">
					{{ getTotal() }}
				</p>
			</div>
		</div>
	</div>

	<ErrorMessage
		class="mt-2"
		v-if="$resources.usePartnerCredits.error"
		:error="$resources.usePartnerCredits.error"
	/>
	<div
		class="float-right w-fit mt-4"
		v-if="step == 'Confirm Checkout' && $account.team"
	>
		<Button
			class="mr-2"
			v-if="$account.team.erpnext_partner"
			appearance="secondary"
			@click="$resources.usePartnerCredits.submit()"
	 		:loading="$resources.usePartnerCredits.loading"
		>
			Use Partner Credits
		</Button>
		<Button
			class="mr-2"
			v-if="!$account.team.erpnext_partner && $account.balance >= creditsToBuy"
			appearance="secondary"
			@click="step = 'Use Existing Credits'"
		>
			Use Existing Credits
		</Button>
		<Button
			appearance="primary"
			@click="$resources.changePlan.submit()"
			:loading="$resources.changePlan.loading"
		>
			Pay Amount
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
				@click="$resources.useCredits.submit()"
				:loading="$resources.useCredits.loading"
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
	name: 'MarketplacePrepaidCredits',
	props: {
		renewal: {
			default: false
		},
		app: '',
		appTitle: '',
		site: '',
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
			step: 'Confirm Checkout',
			clientSecret: null,
			paymentMethod: null,
			publishableKey: null,
			paymentOptions: ['Monthly', 'Annual'],
			selectedOption: 'Monthly',
			planData: null,
			discount_percent: 0,
			subtotal: 0
		};
	},
	mounted() {
		if (!this.renewal) {
			this.$resources.plan.submit();
		} else if (this.renewal) {
			this.$resources.subscriptions.submit();
		}
	},
	watch: {
		selectedOption(newOption, oldOption) {
			if (newOption == 'Monthly') {
				this.discount_percent = 0;
			}
		}
	},
	methods: {
		getSubtotal() {
			let amount = 0;
			let discount = 10; // default discount on combined renewals
			let billed = this.selectedOption === 'Annual' ? 12 : 1;

			if (this.renewal && this.$resources.subscriptions.data) {
				this.$resources.subscriptions.data.forEach(item => {
					amount += item.selected_plan.amount * billed;
				});
			} else {
				amount = this.planData.amount * billed;
				discount = this.planData ? this.planData.discount_percent : 10;
			}

			return {
				amount: amount,
				discount: discount
			};
		},

		getTotal() {
			let subtotal = this.getSubtotal();
			this.subtotal = subtotal.amount;
			this.creditsToBuy = subtotal.amount;

			if (this.selectedOption === 'Annual') {
				subtotal.amount = Math.floor(
					subtotal.amount - (subtotal.discount / 100) * subtotal.amount
				);
				this.discount_percent = subtotal.discount;
			}

			if (this.gstApplicable()) {
				subtotal.amount += subtotal.amount * 0.18;
			}
			this.totalAmount = subtotal.amount;
			return this.totalAmount;
		},

		gstApplicable() {
			if (this.renewal && this.$account.team) {
				if (this.$account.team.country == 'India') {
					return true;
				}
			} else if (
				this.$account.team.country === 'India' &&
				this.planData.gst == 1
			) {
				return true;
			}
			return false;
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
		subscriptions() {
			return {
				method: 'press.api.marketplace.subscriptions',
				auto: false
			};
		},
		plan() {
			return {
				method: 'press.api.marketplace.get_plan',
				params: {
					name: this.plan
				},
				auto: false,
				onSuccess(r) {
					this.planData = r;
					this.creditsToBuy = r.amount;
					if (r.block_monthly === 1) {
						this.selectedOption = 'Annual';
						this.paymentOptions = ['Annual'];
					}
				}
			};
		},
		useCredits() {
			return {
				method: 'press.api.marketplace.use_existing_credits',
				params: {
					site: this.site,
					app: this.app,
					subscription: this.subscription,
					plan: this.plan
				},
				onSuccess(r) {
					this.step = 'Confirm Checkout';
					window.location.reload();
				}
			};
		},
		usePartnerCredits() {
			return {
				method: 'press.api.marketplace.use_partner_credits',
				params: {
					name: this.subscription,
					app: this.app,
					site: this.site,
					plan: this.plan,
					amount: this.totalAmount,
					credits: this.creditsToBuy
				},
				onSuccess(r) {
					window.location.reload();
				}
			};
		},
		changePlan() {
			return {
				method: 'press.api.marketplace.prepaid_saas_payment',
				params: {
					name: this.subscription,
					app: this.app || 'test',
					site: this.site || 'test',
					plan: this.plan || 'test',
					amount: this.totalAmount,
					credits: this.creditsToBuy,
					payment_option: this.selectedOption === 'Annual' ? 12 : 1,
					renewal: this.renewal,
					subscriptions: this.$resources.subscriptions.data
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
