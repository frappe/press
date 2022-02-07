<template>
	<div class="relative">
		<div
			v-if="!ready"
			class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-8 transform"
		>
			<Spinner class="h-5 w-5 text-gray-600" />
		</div>
		<div :class="{ 'opacity-0': !ready }">
			<label class="block">
				<span class="text-sm leading-4 text-gray-700">
					Credit or Debit Card
				</span>
				<div
					class="form-input mt-2 block w-full py-2 pl-3"
					ref="card-element"
				></div>
				<ErrorMessage class="mt-1" :error="cardErrorMessage" />
			</label>
			<Input
				class="mt-4"
				label="Name on Card"
				type="text"
				v-model="billingInformation.cardHolderName"
			/>
			<AddressForm
				v-if="!withoutAddress"
				class="mt-4"
				v-model="billingInformation"
				ref="address-form"
			/>
			<ErrorMessage class="mt-2" :error="errorMessage" />
			<div class="mt-6 flex items-center justify-between">
				<Button type="primary" @click="submit" :loading="addingCard">
					Save Card
				</Button>
				<StripeLogo />
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
			addingCard: false
		};
	},
	async mounted() {
		this.setupCard();

		let { first_name, last_name } = this.$account.user;
		let fullname = first_name + ' ' + last_name;
		this.billingInformation.cardHolderName = fullname;
	},
	resources: {
		countryList: 'press.api.account.country_list',
		billingAddress: {
			method: 'press.api.account.get_billing_information',
			auto: true,
			onSuccess(data) {
				if (data) {
					this.billingInformation.address = data.address_line1;
					this.billingInformation.city = data.city;
					this.billingInformation.state = data.state;
					this.billingInformation.country = data.country;
					this.billingInformation.postal_code = data.pincode;
				}
			}
		}
	},
	methods: {
		async setupCard() {
			let result = await this.$call(
				'press.api.billing.get_publishable_key_and_setup_intent'
			);
			let { publishable_key, setup_intent } = result;
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
		},
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
					try {
						await this.$call('press.api.billing.setup_intent_success', {
							setup_intent: setupIntent,
							address: this.withoutAddress ? null : this.billingInformation
						});
						this.addingCard = false;
						this.$emit('complete');
					} catch (error) {
						this.addingCard = false;
						this.errorMessage = error.messages.join('\n');
					}
				}
			}
		},
		getCountryCode(country) {
			let code = this.$resources.countryList.data.find(
				d => d.name === country
			).code;
			return code.toUpperCase();
		}
	}
};
</script>
