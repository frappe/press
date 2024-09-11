<template>
	<div class="relative">
		<div
			v-if="!ready"
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-8 transform"
		>
			<Spinner class="h-5 w-5 text-gray-600" />
		</div>
		<div :class="{ 'opacity-0': !ready }">
			<div v-show="!tryingMicroCharge">
				<label class="block">
					<span class="block text-xs text-gray-600">
						Credit or Debit Card
					</span>
					<div
						class="form-input mt-2 block h-[unset] w-full py-2 pl-3"
						ref="card-element"
					></div>
					<ErrorMessage class="mt-1" :message="cardErrorMessage" />
				</label>
				<FormControl
					class="mt-4"
					label="Name on Card"
					type="text"
					v-model="cardHolderName"
				/>
			</div>

			<div class="mt-3 space-y-4" v-show="tryingMicroCharge">
				<p class="text-base text-gray-700">
					We are attempting to charge your card with
					<strong>{{ formattedMicroChargeAmount }}</strong> to make sure the
					card works. This amount will be <strong>refunded</strong> back to your
					account.
				</p>

				<Button
					:loading="!microChargeCompleted"
					:loadingText="'Verifying Card'"
				>
					Card Verified
					<template #prefix>
						<GreenCheckIcon class="h-4 w-4" />
					</template>
				</Button>
			</div>

			<ErrorMessage class="mt-2" :message="errorMessage" />

			<div class="mt-6 flex items-center justify-between">
				<StripeLogo />
				<Button
					@click="clearForm"
					v-if="showAddAnotherCardButton"
					iconLeft="plus"
				>
					Add Another Card
				</Button>
				<Button
					v-else-if="!tryingMicroCharge"
					variant="solid"
					@click="submit"
					:loading="addingCard"
				>
					Verify & Save Card
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';
import { toast } from 'vue-sonner';

export default {
	name: 'StripeCard',
	emits: ['complete'],
	components: {
		StripeLogo
	},
	inject: ['team'],
	data() {
		return {
			errorMessage: null,
			cardErrorMessage: null,
			ready: false,
			setupIntent: null,
			cardHolderName: '',
			gstNotApplicable: false,
			addingCard: false,
			tryingMicroCharge: false,
			showAddAnotherCardButton: false,
			microChargeCompleted: false
		};
	},
	async mounted() {
		await this.setupStripeIntent();
	},
	resources: {
		setupIntent() {
			return {
				url: 'press.saas.api.billing.get_publishable_key_and_setup_intent',
				async onSuccess(data) {
					//window.posthog.capture('init_client_add_card', 'fc_signup');
					let { publishable_key, setup_intent } = data;
					this.setupIntent = setup_intent;
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
					this.card.mount(this.$refs['card-element']);

					this.card.addEventListener('change', event => {
						this.cardErrorMessage = event.error?.message || null;
					});
					this.card.addEventListener('ready', () => {
						this.ready = true;
					});
				}
			};
		},
		countryList: 'press.saas.api.billing.country_list',
		setupIntentSuccess() {
			return {
				url: 'press.saas.api.billing.setup_intent_success',
				makeParams({ setupIntent }) {
					return {
						setup_intent: setupIntent
					};
				}
			};
		},
		verifyCardWithMicroCharge() {
			return {
				url: 'press.saas.api.billing.create_payment_intent_for_micro_debit',
				makeParams({ paymentMethodName }) {
					return {
						payment_method_name: paymentMethodName
					};
				}
			};
		}
	},
	methods: {
		async setupStripeIntent() {
			await this.$resources.setupIntent.submit();

			let { first_name, last_name = '' } = this.team?.data?.user_info;
			let fullname = first_name + ' ' + last_name;
			this.cardHolderName = fullname.trimEnd();
		},
		async submit() {
			this.addingCard = true;

			let message;
			if (message) {
				this.errorMessage = message;
				this.addingCard = false;
				return;
			} else {
				this.errorMessage = null;
			}

			const { setupIntent, error } = await this.stripe.confirmCardSetup(
				this.setupIntent.client_secret,
				{
					payment_method: {
						card: this.card,
						billing_details: {
							name: this.cardHolderName,
							address: {
								country: this.getCountryCode(this.team?.data?.country)
							}
						}
					}
				}
			);

			if (error) {
				this.addingCard = false;
				let declineCode = error.decline_code;
				let errorMessage = error.message;

				if (declineCode === 'do_not_honor') {
					this.errorMessage =
						"Your card was declined. It might be due to insufficient funds or you might've exceeded your daily limit. Please try with another card or contact your bank.";
					this.showAddAnotherCardButton = true;
				} else if (declineCode === 'transaction_not_allowed') {
					this.errorMessage =
						'Your card was declined. It might be due to restrictions on your card, like international transactions or online payments. Please try with another card or contact your bank.';
					this.showAddAnotherCardButton = true;
				}
				// fix for duplicate error message
				else if (errorMessage != 'Your card number is incomplete.') {
					this.errorMessage = errorMessage;
				}
			} else {
				if (setupIntent?.status === 'succeeded') {
					this.$resources.setupIntentSuccess.submit(
						{
							setupIntent
						},
						{
							onSuccess: async ({ payment_method_name }) => {
								await this.verifyWithMicroChargeIfApplicable(
									payment_method_name
								);
								this.addingCard = false;
								toast.success('Card added successfully');
							},
							onError: error => {
								console.error(error);
								this.addingCard = false;
								this.errorMessage = error.messages.join('\n');
								toast.error(this.errorMessage);
							}
						}
					);
				}
			}
		},
		async verifyWithMicroChargeIfApplicable(paymentMethodName) {
			const teamCurrency = this.team?.data?.currency;
			const verifyCardsWithMicroCharge = window.verify_cards_with_micro_charge;

			const isMicroChargeApplicable =
				verifyCardsWithMicroCharge === 'Both INR and USD' ||
				(verifyCardsWithMicroCharge == 'Only INR' && teamCurrency === 'INR') ||
				(verifyCardsWithMicroCharge === 'Only USD' && teamCurrency === 'USD');

			if (isMicroChargeApplicable) {
				await this._verifyWithMicroCharge(paymentMethodName);
			} else {
				this.$emit('complete');
			}
		},

		_verifyWithMicroCharge(paymentMethodName) {
			this.tryingMicroCharge = true;
			return this.$resources.verifyCardWithMicroCharge.submit(
				{ paymentMethodName },
				{
					onSuccess: async paymentIntent => {
						let { client_secret } = paymentIntent;
						let payload = await this.stripe.confirmCardPayment(client_secret, {
							payment_method: { card: this.card }
						});
						if (payload.paymentIntent?.status === 'succeeded') {
							this.microChargeCompleted = true;
							this.$emit('complete');
						}
					},
					onError: error => {
						console.error(error);
						this.tryingMicroCharge = false;
						this.errorMessage = error.messages.join('\n');
					}
				}
			);
		},
		getCountryCode(country) {
			let code = this.$resources.countryList.data.find(
				d => d.name === country
			).code;
			return code.toUpperCase();
		},
		async clearForm() {
			this.ready = false;
			this.errorMessage = null;
			this.showAddAnotherCardButton = false;
			this.card = null;
			this.setupStripeIntent();
		}
	},
	computed: {
		formattedMicroChargeAmount() {
			if (!this?.team?.data?.currency) {
				return 0;
			}
			return this.$format.currency(
				this.team?.data?.billing_info?.micro_debit_charge_amount,
				this.team?.data?.currency
			);
		},
		browserTimezone() {
			if (!window.Intl) {
				return null;
			}
			return Intl.DateTimeFormat().resolvedOptions().timeZone;
		}
	}
};
</script>
