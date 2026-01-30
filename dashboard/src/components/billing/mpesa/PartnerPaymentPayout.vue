<template>
	<Dialog :options="{ title: 'Partner Payments Payouts', size: 'lg' }">
		<template #body-content>
			<div class="grid grid-cols-2 gap-4">
				<!-- Filters -->
				<FormControl
					label="Payment Gateway"
					v-model="paymentGateway"
					name="payment_gateway"
					type="combobox"
					:options="paymentGatewayList"
					size="sm"
					variant="subtle"
					class="mb-5"
					placeholder="Enter Payment Gateway"
				/>

				<FormControl
					label="Partner"
					v-model="partner"
					:options="partnerList"
					size="sm"
					variant="subtle"
					type="combobox"
					class="mb-5"
					placeholder="Enter Partner"
				/>

				<FormControl
					label="From Date"
					v-model="fromDate"
					name="from_date"
					autocomplete="off"
					class="mb-5"
					type="date"
					placeholder="Select Start Date"
				/>

				<FormControl
					label="To Date"
					v-model="toDate"
					name="to_date"
					autocomplete="off"
					class="mb-5"
					type="date"
					placeholder="Select End Date"
				/>

				<Button
					@click="fetchPayments"
					variant="solid"
					class="justify-center col-span-2"
				>
					Fetch Payments
				</Button>
			</div>

			<!-- Results Table -->
			<div v-if="payments.length > 0" class="mt-5">
				<table class="w-full border-collapse border border-gray-300">
					<thead>
						<tr>
							<th class="border border-gray-300 p-2">Transaction ID</th>
							<th class="border border-gray-300 p-2">Amount</th>
							<th class="border border-gray-300 p-2">Posting Date</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="payment in payments" :key="payment.name">
							<td class="border border-gray-300 p-2">{{ payment.name }}</td>
							<td class="border border-gray-300 p-2">{{ payment.amount }}</td>
							<td class="border border-gray-300 p-2">
								{{ payment.posting_date }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<div
				v-if="payments.length === 0 && fetchAttempted"
				class="text-center mt-4 text-gray-500"
			>
				No payments found.
			</div>
			<div v-if="payments.length != 0" class="mt-4 flex w-full justify-end">
				<Button
					variant="outline"
					@click="createAndSubmitPayout"
					:loading="paymentInProgress"
				>
					Submit Payments
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { frappeRequest } from 'frappe-ui';

export default {
	name: 'PartnerPaymentPayout',
	data() {
		return {
			paymentGateway: '',
			partner: '',
			fromDate: '',
			toDate: '',
			partnerList: [],
			payments: [],
			fetchAttempted: false,
			paymentGatewayList: [],
		};
	},
	resources: {
		createPaymentPartnerPayout() {
			return {
				url: 'press.api.regional_payments.mpesa.utils.create_payment_partner_payout',
				method: 'POST',
				params: {
					payment_gateway: this.paymentGateway.value,
					payment_partner: this.partner.value,
					from_date: this.fromDate,
					to_date: this.toDate,
					payments: this.payments,
				},
				onSuccess: () => {
					toast.success('Payments submitted successfully');
					this.$emit('close');
				},
				onError: (error) => {
					toast.error(`Error submitting payments: ${error.message}`);
				},
			};
		},
	},
	methods: {
		async createAndSubmitPayout() {
			try {
				this.paymentInProgress = true;
				await this.$resources.createPaymentPartnerPayout.submit();
			} catch (error) {
				toast.error(`Error submitting payments: ${error.message}`);
			} finally {
				this.paymentInProgress = false;
			}
		},
		async fetchPayments() {
			try {
				this.fetchAttempted = true;
				const response = await frappeRequest({
					url: 'press.api.regional_payments.mpesa.utils.fetch_payments',
					method: 'GET',
					params: {
						payment_gateway: this.paymentGateway.value,
						partner: this.partner.value,
						from_date: this.fromDate,
						to_date: this.toDate,
					},
				});
				if (Array.isArray(response)) {
					this.payments = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				toast.error(`Error fetching payments: ${error.message}`);
			}
		},
		async fetchPartners() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_payment_partners',
					method: 'GET',
				});
				if (Array.isArray(response)) {
					this.partnerList = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch teams ${error.message}`;
			}
		},

		async fetchPaymentGateway() {
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_payment_gateway',
					method: 'GET',
				});
				if (Array.isArray(response)) {
					this.paymentGatewayList = response;
				} else {
					console.log('No Data');
				}
			} catch (error) {
				this.errorMessage = `Failed to fetch payment gateway ${error.message}`;
			}
		},
	},
	mounted() {
		this.fetchPartners();
		this.fetchPaymentGateway();
	},
};
</script>

<style scoped>
table {
	width: 100%;
	text-align: left;
	margin-top: 1rem;
}

th,
td {
	padding: 8px 12px;
}
</style>
