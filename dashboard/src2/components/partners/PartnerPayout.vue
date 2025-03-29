<template>
	<div class="container mx-auto p-4">
		<div class="flex justify-between items-center mb-6">
			<h1 class="text-2xl font-bold text-center">Partner Payment Payout</h1>
			<Button
				variant="solid"
				icon-left="plus"
				@click="$router.push({ name: 'PartnerNewPayout' })"
			>
				New Payout
			</Button>
		</div>

		<div class="bg-white rounded-lg shadow p-4 mb-6">
			<table class="w-full text-left border-collapse">
				<thead>
					<tr>
						<th class="p-2 border-b">Payout ID</th>
						<th class="p-2 border-b">Posting Date</th>
						<th class="p-2 border-b">Total Amount</th>
						<th class="p-2 border-b">Commission</th>
						<th class="p-2 border-b">Net Amount</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="payout in paymentPayout" :key="payout.name">
						<td class="p-2 border-b">{{ payout.name }}</td>
						<td class="p-2 border-b">
							{{ formatDate(payout.posting_date) }}
						</td>
						<td class="p-2 border-b">
							{{ formatCurrency(payout.total_amount) }}
						</td>
						<td class="p-2 border-b">
							{{ formatCurrency(payout.commission) }}
						</td>
						<td class="p-2 border-b">
							{{ formatCurrency(payout.net_amount) }}
						</td>
					</tr>
					<tr v-if="paymentPayout.length === 0">
						<td colspan="4" class="p-4 text-center text-gray-500">
							No payouts found
						</td>
					</tr>
				</tbody>
			</table>
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
} from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	components: { FeatherIcon, Button, Autocomplete, Badge },
	data() {
		return {
			partnerInput: '',
			paymentGateway: '',
			from_date: new Date().toISOString().split('T')[0],
			to_date: new Date().toISOString().split('T')[0],

			reconciliationInProgress: false,
			partners: [],
			paymentGateways: [],
			transactions: [],
			paymentPayout: [],
		};
	},
	methods: {
		async fetchPayouts() {
			const response = await frappeRequest({
				url: '/api/method/press.api.regional_payments.mpesa.utils.fetch_payouts',
				method: 'GET',
			});
			if (response.length > 0) {
				this.paymentPayout = response || [];
			} else {
				toast.info('🔍 No transactions found');
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
		this.fetchPayouts();
	},
};
</script>

<style scoped>
.form-input {
	@apply block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm;
}
</style>
