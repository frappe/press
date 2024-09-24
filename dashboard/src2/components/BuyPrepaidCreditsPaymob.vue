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
			<iframe
				v-if="step == 'Add Card Details'"
				ref="paymobIframe"
				class="form-input mt-2 block w-full"
				:src="iframeSrc"
				width="100%"
				height="400px"
				frameborder="0"
				allow="payment"
			></iframe>
			<ErrorMessage class="mt-1" :message="cardErrorMessage" />
		</label>

		<div v-if="step == 'Setting up Paymob'" class="mt-8 flex justify-center">
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
					Proceed to payment using Paymob
				</Button>
			</div>
			<div v-if="step == 'Add Card Details'">
				<Button
					class="ml-2"
					variant="solid"
					@click="onBuyClick"
					:loading="paymentInProgress"
				>
					Make payment via Paymob
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';

export default {
	name: 'BuyPrepaidCreditsPaymob',
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
			iframeSrc: null,
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
					if (
						this.amount < this.minimumAmount &&
						!this.$team.doc.erpnext_partner
					) {
						throw new DashboardError(
							`Amount must be greater than ${this.minimumAmount}`
						);
					}
				},
				async onSuccess(data) {
					this.step = 'Setting up Paymob';
					let { api_key, payment_token, iframe_url } = data;
					
					// Set iframe source
					this.iframeSrc = `${iframe_url}?payment_token=${payment_token}`;
					this.step = 'Add Card Details';
				}
			};
		}
	},
	methods: {
		setupPaymob() {
			this.$resources.createPaymentIntent.submit();
		},
		async onBuyClick() {
			this.paymentInProgress = true;

			// Normally, Paymob handles payment via the iframe. 
			// After a successful transaction, Paymob will notify the backend.
			// You can handle post-payment confirmation here.

			// Simulating the confirmation process
			const isPaymentSuccessful = await this.confirmPayment();

			if (!isPaymentSuccessful) {
				this.errorMessage = 'Payment failed, please try again.';
				this.paymentInProgress = false;
			} else {
				toast.success(
					'Payment processed successfully, we will update your account shortly on confirmation from Paymob'
				);
				this.paymentInProgress = false;
				this.$emit('success');
				this.errorMessage = null;
			}
		},
		async confirmPayment() {
			// Example API call to confirm payment status
			try {
				let response = await fetch('/api/confirm-payment', {
					method: 'POST',
					body: JSON.stringify({ payment_id: this.paymentId })
				});
				let result = await response.json();
				return result.success;
			} catch (error) {
				return false;
			}
		}
	},
	computed: {
		totalAmount() {
			let { currency, billing_info } = this.$account
				? this.$account.team
				: this.$team.doc;
			if (currency === 'EGP') {
				return Number(
					(
						this.amount +
						this.amount * (billing_info.vat_percentage || 0)
					).toFixed(2)
				);
			} else {
				return this.amount;
			}
		}
	}
};
</script>
