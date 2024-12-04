<template>
	
	<div>
		<ErrorMessage
			class="mt-2"
			:message="$resources.createPaymentIntent.error || errorMessage"
			/>
		<FormControl
				:type="'number'"
				size="sm"
				variant="subtle"
				placeholder="Amount in local currency"
				:disabled="true"
				label="Actual Amount"
				v-model="actualAmount"
				class="mb-1 mt-4"
				>
				<template #prefix>
					<div class="grid w-4 place-items-center text-sm text-gray-700">
						E£	
					</div>
				</template>
		</FormControl>
		<span class="text-gray-600 text-xs">applied tax percentage {{ this.taxPercetange }}%</span>
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
			step: 'Get Amount', // Get Amount
			iframeSrc: null,
			errorMessage: null,
			paymentInProgress: false,
			teams: [],
			partnerInput: null,
			taxID: null,
			actualAmount: 0.0,
			currencyExchangeRate: 0.0,
			taxPercetange: 0.0,
			minimumAmount: 10,
			gateway: null,
		};
	},
	resources: {
		createPaymentIntent() {
			return {
				url: 'press.api.local_payments.paymob.billing.intent_to_buying_credits',
				params: {
					amount: this.amount,
					team: this.partnerInput,
					actual_amount: this.actualAmount,
					exchange_rate: this.currencyExchangeRate,
					tax_id: this.taxID,
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
					let { iframe_url } = data;
					this.iframeSrc = iframe_url;
					window.open(data, '_blank');

				}
			};
		},
		getPaymentGateway() {
			return {
				url: "press.api.local_payments.paymob.billing.get_payment_getway",
				params: {
					payment_getway: "Paymob"
				},
				async onSuccess(data) {
					this.getway = data;
					this.taxPercetange = data.taxes_and_charges
					this.teams.push(
						{
							label: data.team_name,
							value: data.team
						}
					)
				}
			};
		},
		fetchTaxId() {
			return {
				url: 'press.api.local_payments.mpesa.utils.get_tax_id',
				params: {},
				async onSuccess(taxID) {
					if (taxID) {
						this.taxID = taxID
					}
				}
			};
		},
		getCurrencyExchangeRate() {
			return {
				url: "press.api.local_payments.paymob.utils.get_exchange_rate",
				params: {
					from_currency: "USD",
					to_currency: "EGP",
				},
				async onSuccess(rate) {
					if (rate) {
						this.currencyExchangeRate = rate
					}
				}
			};
		}
	},
	methods: {
		calcActualAmount() {

			if (!this.amount || !this.currencyExchangeRate || !this.taxPercetange) {
				return 
			}

			// Convert amount to EGP
			const convertedAmount = this.amount * this.currencyExchangeRate;

			// Calculate tax on the converted amount
			const taxAmount = convertedAmount * (this.taxPercetange / 100);

			// Calculate the final amount (including tax)
			this.actualAmount = Number((convertedAmount + taxAmount).toFixed(2));

			return this.actualAmount
		}
	},
	computed: {
		gateWay() {
			if (
					!this.$resources.getPaymentGateway.loading &&
					this.$resources.getPaymentGateway.data && !this.gateway
			) {
					return this.$resources.getPaymentGateway.data;
				}
		},
		actualAmount() {
			return this.calcActualAmount()
		},
		currencyExchangeRate() {
			if (
				!this.$resources.getCurrencyExchangeRate.loading && 
				!this.$resources.getCurrencyExchangeRate.data && !this.exchangeRate
			) {
				return this.$resources.getCurrencyExchangeRate.data;
			}
		}
		
	},
	watch: {
		amount(newAmount) {
			this.calcActualAmount(); // Update actualAmount when amount changes
		},
	},
	mounted() {
		this.$resources.getPaymentGateway.submit()
		this.$resources.fetchTaxId.submit();
		this.$resources.getCurrencyExchangeRate.submit();
		this.calcActualAmount()
	}
};
</script>
