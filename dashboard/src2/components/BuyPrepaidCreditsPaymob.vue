<template>
	<div>
		<div v-if="step == 'Setting up Paymob'" class="mt-8 flex justify-center">
			<Spinner class="h-4 w-4 text-gray-600" />
		</div>
		<ErrorMessage
			class="mt-2"
			:message="$resources.createPaymentIntent.error || errorMessage"
		/>
		<FormControl
			type="autocomplete"
			:options="teams" 
			size="sm"
			variant="subtle"
			placeholder="Select a partner"
			:disabled="false"
			label="Partner"
			v-model="partnerInput" 
			class="mb-5 my-4"
		/>
		<FormControl
			:type="'number'"
			size="sm"
			variant="subtle"
			placeholder="Tax ID"
			:disabled="false"
			label="Company Tax ID"
			v-model="taxID"
			class="mb-5 my-4"
		/>
		<FormControl
			:type="'number'"
			size="sm"
			variant="subtle"
			placeholder="Amount in (Gateway) Currency [Actual Deducable]"
			:disabled="true"
			label="Actual Amount"
			v-model="actualAmount"
			class="mb-2 mt-4"
		/>
		<span class="text-gray-600 text-xs">Amount in (Gateway) Currency [Actual Deducable]<br> Actual Amount = (Amount USD * Exchange Rate) + Tax Amount </span>
		<div class="mt-4 flex w-full justify-end">
			<div v-if="step == 'Get Amount'">
				<Button
					variant="solid"
					@click="$resources.createPaymentIntent.submit()"
					:loading="$resources.createPaymentIntent.loading"
				>
					Proceed to payment using Paymob
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';
import { FormControl } from "frappe-ui";

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
			paymentInProgress: false,
			teams: ["axentor.co"],
			partnerInput: null,
			taxID: null,
			actualAmount: 0.0,
			currencyExchangeRate: 48,
			taxPercetange: 13,
		};
	},
	resources: {
		// TODO: Add the paymob intent endpoint
		createPaymentIntent() {
			return {
				url: 'press.api.billing.create_payment_intent_for_buying_credits',
				params: {
					amount: this.amount
				},
				validate() {
					if (!this.actualAmount || !this.taxID || !this.partnerInput) {
						toast("All Fields Required")
						throw new DashboardError(
							`All Fields Required`
						);
					}
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
		},
		calcActualAmount() {
			this.actualAmount = Number(
					(
						(this.amount * (this.currencyExchangeRate || 0)) + (this.amount * (this.taxPercetange / 100))
					).toFixed(2)
				);
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
	},
	watch: {
		amount(newAmount) {
			this.calcActualAmount(); // Update actualAmount when amount changes
		},
	},
	mounted() {
		this.calcActualAmount()
	}
};
</script>
