<template>
	<div class="relative">
		<div
			v-if="!ready"
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-8 transform"
		>
			<Spinner class="h-5 w-5 text-gray-600" />
		</div>
		<div :class="{ 'opacity-0': !ready }">
			<div>
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
	props: ['secretKey', 'address', 'currency', 'selectedPlan'],
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
			cardHolderName: '',
			gstNotApplicable: false,
			addingCard: false
		};
	},
	async mounted() {
		this.setupCard();
	},
	resources: {
		countryList() {
			return {
				url: 'press.api.account.country_list',
				auto: true
			};
		}
	},
	methods: {
		async setupCard() {
			let result = await this.$call(
				'press.api.developer.marketplace.get_publishable_key_and_setup_intent',
				{ secret_key: this.secretKey }
			);
			//window.posthog.capture('init_client_add_card', 'fc_signup');
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
			if (!this.address) {
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
							name: this.cardHolderName,
							address: {
								line1: this.address.address_line1,
								city: this.address.city,
								state: this.address.state,
								postal_code: this.address.postal_code,
								country: this.getCountryCode(this.address.country)
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
						const { payment_method_name } = await this.$call(
							'press.api.developer.marketplace.setup_intent_success',
							{
								secret_key: this.secretKey,
								setup_intent: setupIntent
							}
						);

						this.addingCard = false;

						await this.$call(
							'press.api.developer.marketplace.change_site_plan',
							{
								secret_key: this.secretKey,
								plan: this.selectedPlan.name
							}
						);
						this.$emit('update:step', 4);
					} catch (error) {
						console.error(error);
						this.addingCard = false;
						this.errorMessage = error.messages.join('\n');
					}
				}
			}
		},
		getCountryCode(country) {
			country = 'India';
			let code = this.$resources.countryList.data.find(
				d => d.name === country
			).code;
			return code.toUpperCase();
		}
	}
};
</script>
