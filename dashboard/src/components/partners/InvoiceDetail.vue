<template>
	<div>
		<div class="overflow-x-auto">
			<table
				class="text w-full border-separate border-spacing-y-2 text-base font-normal text-gray-900"
			>
				<thead class="bg-gray-100">
					<tr class="text-gray-600">
						<th class="rounded-l p-2 text-left font-normal">Resource</th>
						<th class="rounded-l p-2 text-left font-normal">Description</th>
						<th class="whitespace-nowrap p-2 text-right font-normal">Rate</th>
						<th class="whitespace-nowrap p-2 text-right font-normal">
							Quantity
						</th>
						<th class="rounded-r p-2 text-right font-normal">Amount</th>
					</tr>
				</thead>
				<tbody>
					<template v-for="(items, type) in groupedLineItems" :key="type">
						<tr class="mt-1 bg-gray-50">
							<td colspan="100" class="rounded p-2 text-base font-medium">
								{{ type }}
							</td>
						</tr>
						<tr v-for="(row, i) in items" :key="row.idx">
							<td class="py-1 pl-2 pr-2">
								{{ row.document_type }}
							</td>
							<td class="py-1 pl-2 pr-2">
								{{ row.document_name }}
								<span v-if="row.plan" class="text-gray-700">
									({{ formatPlan(row.plan) }}/mo)
								</span>
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ row.rate }}
							</td>
							<td class="py-1 pl-2 pr-2 text-right">
								{{ row.quantity }}
								{{
									[
										'Site',
										'Release Group',
										'Server',
										'Database Server',
									].includes(row.document_type)
										? $format.plural(row.quantity, 'day', 'days')
										: ''
								}}
							</td>
							<td class="py-1 pl-2 pr-2 text-right font-medium">
								{{ row.amount }}
							</td>
						</tr>
					</template>
				</tbody>
			</table>
		</div>
	</div>
</template>
<script>
import { getPlans } from '../../data/plans';

export default {
	name: 'InvoiceDetail',
	props: ['invoiceId'],
	data() {
		return {
			_invoiceItems: null,
		};
	},
	resources: {
		invoiceItems() {
			return {
				url: 'press.api.partner.get_invoice_items',
				makeParams() {
					return { invoice: this.invoiceId };
				},
				auto: true,
				onSuccess(data) {
					this._invoiceItems = data;
				},
			};
		},
	},
	computed: {
		groupedLineItems() {
			if (!this._invoiceItems) return {};
			const groupedLineItems = {};
			for (let item of this._invoiceItems) {
				groupedLineItems[item.user] = groupedLineItems[item.user] || [];
				groupedLineItems[item.user].push(item);
			}
			return groupedLineItems;
		},
	},
	methods: {
		formatPlan(plan) {
			let planDoc = getPlans().find((p) => p.name === plan);
			if (planDoc) {
				let india = this.$team.doc.currency === 'INR';
				return this.$format.userCurrency(
					india ? planDoc.price_inr : planDoc.price_usd,
				);
			}
			return plan;
		},
	},
};
</script>
