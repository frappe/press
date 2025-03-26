<template>
	<div class="container mx-auto p-4">
		<h2 class="text-2xl font-normal mb-6">
			<span class="text-gray-500 opacity-75">Partner Payment Payout / </span>
			<span>New</span>
		</h2>
		<hr />
		<!-- Filters Section -->
		<div class="pt-[50px]">
			<div class="bg-white rounded-lg shadow p-4 mb-6">
				<h2 class="text-lg font-semibold mb-4">Filters</h2>
				<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
					<div>
						<FormControl
							type="autocomplete"
							:options="partners"
							size="sm"
							variant="subtle"
							placeholder="Select Partner"
							:disabled="false"
							label="Partner"
							v-model="partnerInput"
							class="mb-5"
						/>
					</div>
					<div>
						<FormControl
							type="autocomplete"
							:options="paymentGateways"
							size="sm"
							variant="subtle"
							placeholder="Select Gateway"
							label="Payment Gateway"
							v-model="paymentGateway"
							class="mb-5"
						/>
					</div>
					<div>
						<FormControl
							type="date"
							size="sm"
							variant="subtle"
							placeholder="From Date"
							label="From date"
							v-model="from_date"
							class="mb-5"
						/>
					</div>
					<div>
						<FormControl
							type="date"
							size="sm"
							variant="subtle"
							placeholder="To Date"
							label="To date"
							v-model="to_date"
							class="mb-5"
						/>
					</div>
				</div>
				<div class="flex justify-end mt-4 space-x-2">
					<Button
						variant="solid"
						@click="fetchTransactions"
						:loading="fetchPayoutTransactions"
					>
						Fetch Transactions
					</Button>
					<Button
						variant="solid"
						@click="onSubmitPayout"
						:loading="reconciliationInProgress"
					>
						Submit Payout
					</Button>
				</div>
			</div>
		</div>
		<!-- Transactions Table -->
		<div
			v-if="transactions.length > 0"
			class="bg-white rounded-lg shadow p-4 mb-6"
		>
			<h2 class="text-lg font-semibold mb-4">Fetched Transactions</h2>
			<table class="w-full text-left border-collapse">
				<thead>
					<tr>
						<th class="p-2 border-b">Transaction ID</th>
						<th class="p-2 border-b">Amount (USD)</th>
						<th class="p-2 border-b">Posting Date</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="transaction in transactions" :key="transaction.name">
						<td class="p-2 border-b">{{ transaction.name }}</td>
						<td class="p-2 border-b">
							{{ formatCurrency(transaction.amount) }}
						</td>
						<td class="p-2 border-b">
							{{ formatDate(transaction.posting_date) }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Summary Section -->
		<div
			class="bg-white rounded-lg shadow p-4 mb-6"
			v-if="transactions.length > 0"
		>
			<h2 class="text-lg font-semibold mb-4">Summary</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="bg-gray-50 p-3 rounded">
					<div class="text-sm text-gray-500">Total Amount</div>
					<div class="text-xl font-semibold">
						{{ formatCurrency(total_amount) }}
					</div>
				</div>
				<div class="bg-gray-50 p-3 rounded">
					<div class="text-sm text-gray-500">
						Commission ({{ partner_commission }}%)
					</div>
					<div class="text-xl font-semibold">
						{{ formatCurrency(commission) }}
					</div>
				</div>
				<div class="bg-gray-50 p-3 rounded">
					<div class="text-sm text-gray-500">Net Amount</div>
					<div class="text-xl font-semibold">
						{{ formatCurrency(net_amount) }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import {
	FeatherIcon,
	Button,
	Autocomplete,
	Badge,
	createResource,
	frappeRequest,
} from 'frappe-ui';
import FormControl from 'frappe-ui/src/components/FormControl.vue';
import { toast } from 'vue-sonner';

export default {
	components: { FeatherIcon, Button, Autocomplete, Badge },
	data() {
		return {
			partnerInput: '',
			paymentGateway: '',
			partnerCommission: 0,
			from_date: new Date().toISOString().split('T')[0],
			to_date: new Date().toISOString().split('T')[0],

			reconciliationInProgress: false,
			fetchingPayoutTransaction: false,
			partners: [],
			paymentGateways: [],
			transactions: [],
			paymentPayout: [],
			fetchTransactionsResource: createResource({
				url: 'press.api.partner.fetch_payment_transactions',
				debounce: 300,
				onSuccess: (data) => {
					if (data) {
						this.docname = data.name;
						this.doc = data;
					}
				},
			}),
			submitResource: createResource({
				url: '',
				makeParams: () => ({
					doctype: 'Partner Payment Payout',
					name: this.docname,
				}),
				onSuccess: () => {
					this.fetchTransactionsResource.reload();
				},
			}),
		};
	},
	computed: {
		total_amount() {
			return this.transactions.reduce(
				(acc, transaction) => acc + transaction.amount,
				0,
			);
		},
		commission() {
			return (this.total_amount * this.partnerCommission) / 100;
		},
		net_amount() {
			return this.total_amount - this.commission;
		},
	},
	resources: {
		submitPaymentPayouts() {
			return {
				url: 'press.press.doctype.partner_payment_payout.partner_payment_payout.submit_payment_payout',
				params: {
					partner: this.partnerInput.value,
					payment_gateway: this.paymentGateway.value,
					from_date: this.from_date,
					to_date: this.to_date,
					partner_commission: this.partnerCommission,
					transactions: this.transactions,
				},
			};
		},
	},
	methods: {
		async onSubmitPayout() {
			this.reconciliationInProgress = true;
			try {
				if (
					!this.partnerInput ||
					!this.paymentGateway ||
					this.transactions.length === 0
				) {
					toast.error(
						'Please select partner, payment gateway and fetch transactions first',
					);
					return;
				}

				const result = await this.$resources.submitPaymentPayouts.submit({
					partner: this.partnerInput.value,
					payment_gateway: this.paymentGateway.value,
					from_date: this.from_date,
					to_date: this.to_date,
					partner_commission: this.partnerCommission,
					transactions: this.transactions,
				});

				if (result) {
					toast.success(
						`
          💰 Payout Submitted Successfully!
          ━━━━━━━━━━━━━━━━
          💵 Total: ${this.formatCurrency(result.total_amount)}
          📉 Commission: ${this.formatCurrency(result.commission)} (${this.partnerCommission}%)
          🏦 Net Amount: ${this.formatCurrency(result.net_amount)}
        `,
						{
							duration: 1000,
							onAutoClose: () => {
								this.$router.push({ name: 'PartnerPayout' });
							},
						},
					);
				}
			} catch (error) {
				toast.error(error.message || 'Failed to submit payout');
			} finally {
				this.reconciliationInProgress = false;
			}
		},

		async fetchTransactions() {
			this.fetchPayoutTransactions = true;
			if (!this.partnerInput || !this.paymentGateway) {
				return 'Please fill required values';
			}
			const response = await frappeRequest({
				url: '/api/method/press.api.regional_payments.mpesa.utils.fetch_payments',
				method: 'GET',
				params: {
					partner: this.partnerInput.value,
					payment_gateway: this.paymentGateway.value,
					from_date: this.from_date,
					to_date: this.to_date,
				},
			});
			if (response.length > 0) {
				this.transactions = response || [];
				this.fetchPayoutTransactions = false;
			} else {
				toast.info('🔍 No transactions found');
			}
		},

		submitPayout() {
			this.submitResource.submit();
		},
		resetForm() {
			this.partnerInput = '';
			this.paymentGateway = '';
			this.transactions = [];
		},
		async fetchPartners() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_mpesa_payment_partners',
					method: 'GET',
				});
				if (Array.isArray(response)) {
					this.partners = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch teams ${error.message}`;
			}
		},
		async fetchPaymentGateways() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_payment_gateways',
					method: 'GET',
					params: {
						payment_partner: this.partnerInput.value,
					},
				});
				if (Array.isArray(response)) {
					this.paymentGateways = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch teams ${error.message}`;
			}
		},
		async fetchPercentageCommission() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.fetch_percentage_commission',
					method: 'GET',
					params: {
						partner: this.partnerInput.value,
					},
				});
				if (response) {
					this.partnerCommission = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch teams ${error.message}`;
			}
		},

		formatCurrency(value) {
			return new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: 'USD',
			}).format(value);
		},
		formatDate(value) {
			return new Date(value).toLocaleDateString();
		},
	},

	mounted() {
		this.fetchPartners();
	},
	watch: {
		partnerInput() {
			this.fetchPaymentGateways();
			this.fetchPercentageCommission();
		},
	},
};
</script>
