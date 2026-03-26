<template>
	<div>
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<FBreadcrumbs :items="breadcrumbs" />
			</Header>
		</div>

		<div class="mx-5">
			<!-- Filters Section -->
			<div class="pt-[20px]">
				<div class="bg-white rounded-lg shadow p-4 mb-6">
					<h2 class="text-lg mb-4">Filters</h2>
					<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
						<div>
							<FormControl
								type="combobox"
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
								type="combobox"
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
								label="To date"
								v-model="to_date"
								class="mb-5"
							/>
						</div>
					</div>
					<div class="flex justify-end mt-4 space-x-2">
						<Button
							:variant="transactions.length > 0 ? 'subtle' : 'solid'"
							@click="$resources.fetchTransactions.submit()"
							:loading="fetchPayoutTransactions"
							:disabled="!Boolean(partnerInput && paymentGateway)"
						>
							Fetch Transactions
						</Button>
						<Button
							variant="solid"
							@click="$resources.submitPaymentPayout.submit()"
							:loading="reconciliationInProgress"
							:disabled="Boolean(transactions.length === 0)"
						>
							Submit Payout
						</Button>
					</div>
				</div>
			</div>
			<!-- Transaction Table -->
			<div
				v-if="transactions.length > 0"
				class="bg-white rounded-lg shadow p-4 mb-6"
			>
				<h2 class="text-lg mb-4">Fetched Transactions</h2>
				<ObjectList :options="transactionOptions" />
			</div>

			<!-- Summary Section -->
			<div
				class="bg-white rounded-lg shadow p-4 mb-6"
				v-if="transactions.length > 0"
			>
				<h2 class="text-lg mb-4">Summary</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div class="bg-gray-50 p-3 rounded">
						<div class="text-sm text-gray-500">Total Amount</div>
						<div class="text-xl font-semibold">
							{{ formatCurrency(total_amount) }}
						</div>
					</div>
					<div class="bg-gray-50 p-3 rounded">
						<div class="text-sm text-gray-500">
							Commission ({{ partnerCommission }}%)
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
	</div>
</template>

<script>
import {
	FeatherIcon,
	Button,
	Autocomplete,
	Badge,
	frappeRequest,
	Breadcrumbs,
} from 'frappe-ui';
import { toast } from 'vue-sonner';
import ObjectList from '../components/ObjectList.vue';
import Header from '../components/Header.vue';

export default {
	components: {
		FeatherIcon,
		Button,
		Autocomplete,
		Badge,
		ObjectList,
		FBreadcrumbs: Breadcrumbs,
		Header,
	},
	data() {
		return {
			partnerInput: '',
			paymentGateway: '',
			partnerCommission: this.$team.doc.erpnext_partner ? 10 : 5,
			from_date: new Date().toISOString().split('T')[0],
			to_date: new Date().toISOString().split('T')[0],

			reconciliationInProgress: false,
			fetchPayoutTransactions: false,
			partners: [],
			paymentGateways: [],
			transactions: [],
			paymentPayout: [],
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
		transactionOptions() {
			return {
				columns: [
					{ label: 'Transaction ID', fieldname: 'name' },
					{
						label: 'Amount (USD)',
						fieldname: 'amount',
						format: (val) => this.formatCurrency(val),
					},
					{
						label: 'Posting Date',
						fieldname: 'posting_date',
						format: (val) =>
							Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'short',
								day: 'numeric',
							}).format(new Date(val)),
					},
				],
				data: () => this.transactions,
				emptyStateText: 'No transactions fetched',
			};
		},
		breadcrumbs() {
			return [
				{ label: 'Partner Payment Payout', route: '/partners/payment-payout' },
				{ label: 'New Payment Payout', route: '/payment-payout/New' },
			];
		},
	},
	resources: {
		submitPaymentPayout() {
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
				validate: () => {
					if (this.transactions.length === 0) {
						toast.error('No transactions to submit');
						return false;
					}
				},
				onSuccess: (data) => {
					if (data) {
						toast.success('Payout Submitted Successfully!', {
							duration: 1000,
							onAutoClose: () => {
								this.$router.push({ name: 'PartnerPayout' });
							},
						});
					} else {
						toast.error('Failed to submit payout');
					}
				},
			};
		},
		fetchTransactions() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.fetch_payments',
				debounce: 300,
				params: {
					partner: this.partnerInput.value,
					payment_gateway: this.paymentGateway.value,
					from_date: this.from_date,
					to_date: this.to_date,
				},
				onSuccess: (data) => {
					if (data.length > 0) {
						this.transactions = data || [];
						this.fetchPayoutTransactions = false;
					} else {
						toast.info('No transactions found');
						this.fetchPayoutTransactions = false;
					}
				},
			};
		},
		fetchPartners() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.display_mpesa_payment_partners',
				auto: true,
				onSuccess: (data) => {
					if (Array.isArray(data)) {
						this.partners = data;
					} else {
						console.log('No Data');
					}
				},
			};
		},
	},
	methods: {
		async fetchPaymentGateways() {
			try {
				const response = await frappeRequest({
					url: 'press.api.regional_payments.mpesa.utils.display_payment_gateways',
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
					url: 'press.api.regional_payments.mpesa.utils.fetch_percentage_commission',
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
	watch: {
		partnerInput() {
			this.fetchPaymentGateways();
			this.fetchPercentageCommission();
		},
	},
};
</script>
