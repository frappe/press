<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'BillingBalances',
	props: ['tab'],
	components: {
		ObjectList
	},
	computed: {
		options() {
			return {
				doctype: 'Balance Transaction',
				fields: ['type', 'source', 'invoice'],
				columns: [
					{
						label: 'Date',
						fieldname: 'creation',
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric'
							}).format(new Date(value));
						}
					},
					{
						label: 'Description',
						format(value, row) {
							if (row.type === 'Applied To Invoice' && row.invoice) {
								return `Applied to Invoice ${row.invoice}`;
							}

							return row.amount < 0 ? row.type : row.source;
						}
					},
					{
						label: 'Amount',
						fieldname: 'amount',
						format: this.formatCurrency
					},
					{
						label: 'Balance',
						fieldname: 'ending_balance',
						format: this.$format.userCurrency
					}
				],
				filters: {
					docstatus: 1,
					team: this.$team.name
				},
				orderBy: 'creation desc'
			};
		}
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return this.$format.userCurrency(value);
		}
	}
};
</script>
