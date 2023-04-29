<template>
	<div v-if="plan" class="grid grid-cols-1 gap-0 sm:grid-cols-2 h-screen">
		<div
			class="flex flex-col w-full px-10 mx-auto justify-center bg-gray-50 max-h-full"
		>
			<div
				class="text-sm cursor-pointer w-fit absolute top-1 left-1"
				v-on:click="$emit('update:step', 2)"
			>
				← Back to Plans
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">Plan</span>
				<span class="text-base font-semibold">{{ plan.plan }}</span>
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">Amount</span>
				<span class="text-base font-semibold">{{
					currency == 'INR' ? '₹' + amount() : '$' + amount()
				}}</span>
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">Billing</span>
				<Input
					:disabled="stripePayment"
					type="select"
					:options="['Monthly', 'Annual']"
					v-model="billing"
				/>
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">Discount</span>
				<span class="text-base font-semibold text-green-500">{{
					discount() ? plan.discount_percent + '%' : '-'
				}}</span>
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">GST(if applicable)</span>
				<span class="text-base font-semibold text-red-500">{{
					gst() ? '18%' : '-'
				}}</span>
			</div>
			<div class="flex justify-between my-2">
				<span class="text-base">Total</span>
				<span class="text-base font-semibold">{{
					currency == 'INR' ? '₹' + getTotal() : '$' + getTotal()
				}}</span>
			</div>
			<ErrorMessage
				class="mt-2"
				:message="confirmError"
			/>
			<Button
				v-if="!stripePayment"
				class="mt-4"
				appearance="primary"
				:loading="$resources.handlePayment.loading"
				@click="$resources.handlePayment.submit()"
			>
				Confirm Payment
			</Button>
		</div>

		<!-- Stripe -->
		<div class="flex justify-center h-full w-full">
			<div class="flex flex-col my-auto w-64 h-20">
				<div id="card" 
					class="form-input mt-2 block w-full py-2 pl-3" :class="{ hidden: 'card' == null }"
					ref="card-element"></div>
					<ErrorMessage
						class="mt-2"
						:message="errorMessage"
					/>
					<div class="flex justify-between" >
						<StripeLogo
							class="mt-4 justify-self-end"
							:loading="$resources.handlePayment.loading"
						/>
					<Button
						v-if="card != null"
						class="mt-4"
						appearance="primary"
						:loading="$resources.handlePayment.loading"
						@click="buy"
					>
						Pay Now
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';

export default {
	name: 'CheckoutPayment',
	components: {
		StripeLogo
	},
	props: [
		'plan',
		'currency',
		'selectedSubscription',
		'selectedPlan',
		'step',
		'secretKey'
	],
	data() {
		return {
			billing: 'Annual',
			total: 0,
			card: null,
			stripePayment: false,
			errorMessage: null,
			confirmError: null,
		};
	},
	resources: {
		handlePayment() {
			return {
				method: 'press.api.developer.marketplace.saas_payment',
				params: {
					secret_key: this.secretKey,
					data: {
						sub_name: this.selectedSubscription.name,
						new_plan: this.selectedPlan,
						app: this.selectedSubscription.app,
						site: this.selectedSubscription.site,
						total: this.total,
						billing: this.billing.toLowerCase()
					}
				},
				async onSuccess(r) {
					if (r) {
						this.clientSecret = r.client_secret;
						this.stripePayment = true;
						this.stripe = await loadStripe(r.publishable_key);
						this.elements = this.stripe.elements({
							clientSecret: r.client_secret
						});

						// theme
						let theme = this.$theme;
						let style = {
							base: {
								color: theme.colors.black,
								fontFamily: theme.fontFamily.sans.join(', '),
								fontSmoothing: 'antialiased',
								padding: '4px',
								fontSize: '14px',
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
						this.card.mount(this.$refs['card-element']);
						this.confirmError = e
					} else {
						this.confirmError = e
					}
				},
				onError(e) {
					this.confirmError = e
				}
			};
		}
	},
	methods: {
		amount() {
			let multiple = this.billing === 'Annual' ? 12 : 1;
			return this.currency === 'INR'
				? this.plan.price_inr * multiple
				: this.plan.price_usd * multiple;
		},
		discount() {
			return this.plan.discount_percent > 0 && this.billing === 'Annual';
		},
		gst() {
			return this.plan.gst === 1 && this.currency === 'INR';
		},
		getTotal() {
			let total = this.amount();
			if (this.discount()) {
				total = total - total * (this.plan.discount_percent / 100);
			}
			if (this.gst()) {
				total = total + total * 0.18;
			}
			this.total = total;
			return total;
		},
		async buy() {
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
				this.creditsToBuy = null;
			}
		}
	}
};
</script>
