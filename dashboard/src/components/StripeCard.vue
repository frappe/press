<template>
	<div :class="{ 'opacity-0': !ready }">
		<label class="block">
			<span class="text-gray-800">Name on Card</span>
			<input
				class="block w-full mt-2 shadow form-input"
				type="text"
				v-model="cardholderName"
			/>
		</label>

		<label class="block mt-4">
			<span class="text-gray-800">Credit or Debit Card</span>
			<div
				class="block w-full py-3 mt-2 shadow form-input"
				ref="card-element"
			></div>
		</label>
		<ErrorMessage class="mt-1" v-if="errorMessage">
			{{ errorMessage }}
		</ErrorMessage>

		<Button
			class="mt-6"
			type="primary"
			@click="submit"
			:disabled="state === 'Working'"
		>
			Authorize Card for Payments
		</Button>
	</div>
</template>

<script>
import { loadStripe } from '@stripe/stripe-js';
import resolveConfig from 'tailwindcss/resolveConfig';
import config from '@/../tailwind.config.js';

export default {
	name: 'StripeCard',
	data() {
		return {
			errorMessage: null,
			ready: false,
			setupIntent: null,
			cardholderName: null,
			state: null
		};
	},
	async mounted() {
		let result = await this.$call(
			'press.api.billing.get_publishable_key_and_setup_intent'
		);
		let { publishable_key, setup_intent } = result;
		this.setupIntent = setup_intent;
		this.stripe = await loadStripe(publishable_key);
		this.elements = this.stripe.elements();
		let { theme } = resolveConfig(config);
		let style = {
			base: {
				color: theme.colors.black,
				fontFamily: theme.fontFamily.sans.join(', '),
				fontSmoothing: 'antialiased',
				fontSize: '16px',
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
			style: style,
			classes: {
				complete: '',
				focus: 'shadow-outline-blue'
			}
		});
		this.card.mount(this.$refs['card-element']);

		this.card.addEventListener('change', event => {
			this.errorMessage = event.error?.message || null;
		});
		this.card.addEventListener('ready', () => {
			this.ready = true;
		});
	},
	methods: {
		async submit() {
			this.state = 'Working';
			const { setupIntent, error } = await this.stripe.confirmCardSetup(
				this.setupIntent.client_secret,
				{
					payment_method: {
						card: this.card,
						billing_details: {
							name: this.cardholderName
						}
					}
				}
			);
			this.state = null;

			if (error) {
				this.errorMessage = error;
			} else {
				if (setupIntent.status === 'succeeded') {
					this.$emit('complete');
				}
			}
		}
	}
};
</script>

<style></style>
