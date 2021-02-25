<template>
	<div>
		<div v-if="doc" class="overflow-x-auto">
			<table class="w-full text-sm text">
				<thead>
					<tr class="text-gray-600">
						<th class="py-3 pr-2 font-normal text-left border-b">
							Description
						</th>
						<th
							class="py-3 pr-2 font-normal text-right border-b whitespace-nowrap"
						>
							Rate
						</th>
						<th class="py-3 pr-2 font-normal text-right border-b">
							Amount
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, i) in doc.items" :key="row.idx">
						<td class="py-3 pr-2 border-b">
							{{ row.description || row.document_name }}
						</td>
						<td class="py-3 pr-2 text-right border-b">
							{{ row.rate }} x {{ row.quantity }}
						</td>
						<td class="py-3 pr-2 font-semibold text-right border-b">
							{{ doc.formatted.items[i].amount }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td></td>
						<td class="pt-4 pb-2 pr-2 font-semibold text-right">Grand Total</td>
						<td class="pt-4 pb-2 pr-2 font-semibold text-right whitespace-nowrap">
							{{ doc.formatted.total }}
						</td>
					</tr>
					<template v-if="doc.total !== doc.amount_due && doc.docstatus == 1">
						<tr>
							<td></td>
							<td class="pr-2 text-right">Applied Balance:</td>
							<td class="py-3 pr-2 font-semibold text-right whitespace-nowrap">
								- {{ doc.formatted.applied_credits }}
							</td>
						</tr>
						<tr>
							<td></td>
							<td class="pr-2 text-right">Amount Due:</td>
							<td class="py-3 pr-2 font-semibold text-right whitespace-nowrap">
								{{ doc.formatted.amount_due }}
							</td>
						</tr>
					</template>
				</tfoot>
			</table>
		</div>
		<div class="py-20 text-center" v-if="$resources.doc.loading">
			<Button :loading="true">Loading</Button>
		</div>
	</div>
</template>
<script>
export default {
	name: 'InvoiceUsageTable',
	props: ['invoice', 'invoiceDoc'],
	resources: {
		doc() {
			return {
				method: 'press.api.billing.get_invoice_usage',
				params: { invoice: this.invoice },
				auto: this.invoice,
				onSuccess(doc) {
					this.$emit('doc', doc);
				}
			};
		}
	},
	watch: {
		invoice(value) {
			if (value) {
				this.$resources.doc.fetch();
			}
		}
	},
	computed: {
		doc() {
			return this.invoiceDoc || this.$resources.doc.data;
		}
	}
};
</script>
