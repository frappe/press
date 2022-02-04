<template>
	<Card v-if="invoice" :title="title">
		<template #actions-left>
			<Button route="/account/billing"> ← Back </Button>
		</template>
		<InvoiceUsageTable :invoice="invoice" @doc="doc = $event" />
	</Card>
</template>
<script>
import InvoiceUsageTable from './InvoiceUsageTable.vue';
export default {
	name: 'InvoiceUsageCard',
	props: ['invoice'],
	components: {
		InvoiceUsageTable
	},
	data() {
		return {
			doc: null
		};
	},
	computed: {
		title() {
			let doc = this.doc;
			if (!doc) {
				return '';
			}
			if (!doc.period_start || !doc.period_end) {
				return `Invoice Details for ${this.invoice}`;
			}
			let periodStart = this.$date(doc.period_start);
			let periodEnd = this.$date(doc.period_end);
			let start = periodStart.toLocaleString({ month: 'long', day: 'numeric' });
			let end = periodEnd.toLocaleString({ month: 'short', day: 'numeric' });
			return `Invoice for ${start} - ${end} ${periodEnd.year}`;
		}
	}
};
</script>
