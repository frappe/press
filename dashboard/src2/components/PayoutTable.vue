<template>
	<div>
		<div v-if="doc" class="overflow-x-auto">
			<table
				class="text w-full border-separate border-spacing-y-2 text-base font-normal text-gray-900"
			>
				<thead class="bg-gray-100">
					<tr class="text-gray-600">
						<th class="rounded-l p-2 text-left font-normal">App</th>
						<th class="rounded-l p-2 text-left font-normal">Site</th>
						<th class="whitespace-nowrap p-2 text-right font-normal">Rate</th>
						<th class="whitespace-nowrap p-2 text-right font-normal">Total</th>
						<th class="rounded-r p-2 text-right font-normal">Fee</th>
						<th class="rounded-r p-2 text-right font-normal">Commission</th>
						<th class="rounded-r p-2 text-right font-normal">Net Amount</th>
					</tr>
				</thead>
				<tbody>
					<template v-for="(row, i) in doc.items" :key="row.idx">
						<tr>
							<td class="py-1 pl-2 pr-2">
								{{ row.document_name }}
							</td>
							<td class="py-1 pl-2 pr-2">
								{{ row.site }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ formatCurrency(row.rate, row.currency) }} X
								{{ row.quantity }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ formatCurrency(row.total_amount, row.currency) }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ formatCurrency(row.gateway_fee, row.currency) }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ formatCurrency(row.commission, row.currency) }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ formatCurrency(row.net_amount, row.currency) }}
							</td>
						</tr>
					</template>
				</tbody>
				<tfoot>
					<tr>
						<td></td>
						<td></td>
						<td></td>
						<td></td>
						<td></td>
						<td class="pb-2 pr-2 pt-4 text-right font-medium">Total Payout</td>
						<td class="whitespace-nowrap pb-2 pr-2 pt-4 text-right font-medium">
							{{ formatCurrency(doc.net_total_usd, 'USD') }} +
							{{ formatCurrency(doc.net_total_inr, 'INR') }}
						</td>
					</tr>
				</tfoot>
			</table>
		</div>
		<div class="py-20 text-center" v-if="$resources.invoice.loading">
			<Button :loading="true">Loading</Button>
		</div>
	</div>
</template>
<script>
export default {
	name: 'PayoutTable',
	props: ['payoutId'],
	resources: {
		invoice() {
			return {
				type: 'document',
				doctype: 'Payout Order',
				name: this.payoutId
			};
		}
	},
	computed: {
		doc() {
			return this.$resources.invoice.doc;
		}
	},
	methods: {
		formatCurrency(value, currency) {
			return this.$format.currency(value, currency);
		}
	}
};
</script>
