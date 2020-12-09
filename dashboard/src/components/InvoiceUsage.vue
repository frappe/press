<template>
	<Dialog
		v-if="show"
		:title="title"
		:show="show"
		@change="$emit('update:invoice', $event)"
	>
		<div v-if="doc" class="overflow-x-auto">
			<table class="w-full text-sm text">
				<thead class="bg-blue-50">
					<tr>
						<th class="py-2 pl-2 pr-2 font-semibold border-b border-blue-100">
							Description
						</th>
						<th
							class="py-2 pr-2 font-semibold text-right whitespace-no-wrap border-b border-blue-100"
						>
							Rate
						</th>
						<th
							class="py-2 pr-2 font-semibold text-right border-b border-blue-100"
						>
							Amount
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in doc.items" :key="row.idx">
						<td class="py-2 pl-2 pr-2 border-b">
							{{ row.description || row.document_name }}
						</td>
						<td class="py-2 pr-2 text-right border-b">
							{{ row.rate }} x {{ row.quantity }}
						</td>
						<td class="py-2 pr-2 text-right border-b">
							{{ row.amount }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr>
						<td class="pt-4 pb-2 pl-2">
							<a
								v-if="doc.status == 'Paid' && doc.invoice_pdf"
								class="inline-flex items-center justify-center text-base text-blue-500"
								:href="doc.invoice_pdf"
								target="_blank"
							>
								Download Invoice
								<FeatherIcon name="arrow-right" class="w-4 h-4 ml-2" />
							</a>
						</td>
						<td class="pt-4 pb-2 pr-2 text-right">Total:</td>
						<td class="pt-4 pb-2 pr-2 font-semibold text-right whitespace-no-wrap">
							{{ doc.formatted.total }}
						</td>
					</tr>
					<template v-if="doc.total !== doc.amount_due">
						<tr>
							<td></td>
							<td class="pr-2 text-right">Applied Balance:</td>
							<td class="py-2 pr-2 font-semibold text-right whitespace-no-wrap">
								- {{ doc.formatted.applied_credits }}
							</td>
						</tr>
						<tr>
							<td></td>
							<td class="pr-2 text-right">Amount Due:</td>
							<td class="py-2 pr-2 font-semibold text-right whitespace-no-wrap">
								{{ doc.formatted.amount_due }}
							</td>
						</tr>
					</template>
				</tfoot>
			</table>
		</div>
	</Dialog>
</template>
<script>
export default {
	name: 'InvoiceUsage',
	props: ['invoice'],
	resources: {
		doc() {
			return {
				method: 'press.api.billing.get_invoice_usage',
				params: { invoice: this.invoice }
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
	mounted() {
		if (this.invoice) {
			this.$resources.doc.fetch();
		}
	},
	computed: {
		doc() {
			return this.$resources.doc.data;
		},
		show() {
			return Boolean(this.invoice && this.doc);
		},
		title() {
			if (!this.doc) {
				return '';
			}
			if (!this.doc.period_start || !this.doc.period_end) {
				return `Invoice Details for ${this.invoice}`;
			}
			let periodStart = this.$date(this.doc.period_start);
			let periodEnd = this.$date(this.doc.period_end);
			let start = periodStart.toLocaleString({ month: 'long', day: 'numeric' });
			let end = periodEnd.toLocaleString({ month: 'short', day: 'numeric' });
			return `Invoice Details for ${start} - ${end} ${periodEnd.year}`;
		}
	}
};
</script>
