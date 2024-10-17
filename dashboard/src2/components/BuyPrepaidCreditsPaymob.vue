<template>
	<div>
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
			step: 'Get Amount', // Get Amount
			iframeSrc: null,
			errorMessage: null,
			paymentInProgress: false,
			teams: [],
			partnerInput: null,
			taxID: null,
			actualAmount: 0.0,
			currencyExchangeRate: 48,
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
					actualAmount: this.actualAmount,
					exchange_rate: this.currencyExchangeRate,
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
					console.log(data, iframe_url)
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
		}
	},
	methods: {
		calcActualAmount() {
			this.actualAmount = Number(
					(
						(this.amount * (this.currencyExchangeRate || 0)) + (this.amount * (this.taxPercetange / 100))
					).toFixed(2)
			);
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
		}
		
	},
	watch: {
		amount(newAmount) {
			this.calcActualAmount(); // Update actualAmount when amount changes
		},
	},
	mounted() {
		this.$resources.getPaymentGateway.submit()
		this.calcActualAmount()
	}
};
</script>
