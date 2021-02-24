<template>
	<Card title="Upcoming Invoice Summary" :subtitle="invoicePeriod">
		<InvoiceUsageTable :invoiceDoc="invoiceDoc" />
	</Card>
</template>
<script>
import InvoiceUsageTable from '@/components/InvoiceUsageTable.vue';
export default {
	name: 'AccountBillingUpcomingInvoice',
	props: ['invoiceDoc'],
	components: {
		InvoiceUsageTable
	},
	computed: {
		invoicePeriod() {
			if (!this.invoiceDoc) {
				return '';
			}
			let start = this.$date(this.invoiceDoc.period_start);
			let end = this.$date(this.invoiceDoc.period_end);

			return `${start.toFormat('d MMM')} - ${end.toFormat('d MMM yyyy')}`;
		}
	}
};
</script>
