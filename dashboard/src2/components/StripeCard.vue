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
					v-model="billingInformation.cardHolderName"
				/>
				<AddressForm
					v-if="!withoutAddress"
					class="mt-4"
					v-model:address="billingInformation"
					ref="address-form"
				/>
			</div>

			<div class="mt-3" v-show="tryingMicroCharge">
				<p class="text-lg text-gray-800">
					We are attempting to charge your card with
					<strong>{{ formattedMicroChargeAmount }}</strong> to make sure the
					card works. This amount will be <strong>refunded</strong> back to your
					account.
				</p>

				<Button class="mt-2" :loading="true">Attempting Test Charge</Button>
			</div>

			<ErrorMessage class="mt-2" :message="errorMessage" />

			<div class="mt-6 flex items-center justify-between">
				<StripeLogo />
				<Button variant="solid" @click="submit" :loading="addingCard">
					Save Card
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import AddressForm from '@/components/AddressForm.vue';
import StripeLogo from '@/components/StripeLogo.vue';
import { loadStripe } from '@stripe/stripe-js';

export default {
	name: 'StripeCard',
	props: ['withoutAddress'],
	emits: ['complete'],
	components: {
		AddressForm,
		StripeLogo
	},
	data() {
		return {
			errorMessage: null,
			cardErrorMessage: null,
			ready: false,
			setupIntent: null,
			billingInformation: {
				cardHolderName: '',
				country: '',
				gstin: ''
			},
			gstNotApplicable: false,
			addingCard: false,
			tryingMicroCharge: false
		};
	},
	async mounted() {
		await this.$resources.setupIntent.submit();

		let { first_name, last_name = '' } = this.$team.doc.user_info;
		let fullname = first_name + ' ' + last_name;
		this.billingInformation.cardHolderName = fullname.trimEnd();
	},
	resources: {
		setupIntent() {
			return {
				url: 'press.api.billing.get_publishable_key_and_setup_intent',
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
		countryList: 'press.api.account.country_list',
		billingAddress() {
			return {
				url: 'press.api.account.get_billing_information',
				params: {
					timezone: this.browserTimezone
				},
				auto: true,
				onSuccess(data) {
					this.billingInformation.country = data?.country;
					this.billingInformation.address = data?.address_line1;
					this.billingInformation.city = data?.city;
					this.billingInformation.state = data?.state;
					this.billingInformation.postal_code = data?.pincode;
				}
			};
		},
		setupIntentSuccess() {
			return {
				url: 'press.api.billing.setup_intent_success',
				makeParams({ setupIntent }) {
					return {
						setup_intent: setupIntent,
						address: this.withoutAddress ? null : this.billingInformation
					};
				}
			};
		},
		verifyCardWithMicroCharge() {
			return {
				url: 'press.api.billing.create_payment_intent_for_micro_debit',
				makeParams({ paymentMethodName }) {
					return {
						payment_method_name: paymentMethodName
					};
				}
			};
		}
	},
	methods: {
		async submit() {
			this.addingCard = true;

			let message;
			if (!this.withoutAddress) {
				message = await this.$refs['address-form'].validateValues();
			}
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
							name: this.billingInformation.cardHolderName,
							address: {
								line1: this.billingInformation.address,
								city: this.billingInformation.city,
								state: this.billingInformation.state,
								postal_code: this.billingInformation.postal_code,
								country: this.getCountryCode(this.billingInformation.country)
							}
						}
					}
				}
			);

			if (error) {
				this.addingCard = false;
				let errorMessage = error.message;
				// fix for duplicate error message
				if (errorMessage != 'Your card number is incomplete.') {
					this.errorMessage = errorMessage;
				}
			} else {
				if (setupIntent.status === 'succeeded') {
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
							},
							onError: error => {
								console.error(error);
								this.addingCard = false;
								this.errorMessage = error.messages.join('\n');
							}
						}
					);
				}
			}
		},
		async verifyWithMicroChargeIfApplicable(paymentMethodName) {
			const teamCurrency = this.$team.doc.currency;
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
						if (payload.paymentIntent.status === 'succeeded') {
							this.$emit('complete');
						}
						this.tryingMicroCharge = false;
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
		}
	},
	computed: {
		formattedMicroChargeAmount() {
			const isINR = this.$team.doc.currency === 'INR';
			return isINR ? '₹50' : '$0.5';
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
