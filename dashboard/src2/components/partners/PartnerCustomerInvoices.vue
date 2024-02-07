<template>
	<div>
		<ObjectList :options="options" />
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
import { userCurrency } from '../../utils/format';
import dayjs from '../../utils/dayjs';

export default {
	name: 'PartnerCustomerInvoices',
	props: ['customerTeam'],
	components: {
		ObjectList
	},
	data() {
		return {
			team: this.customerTeam
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Invoice',
				fields: ['type'],
				columns: [
					{ label: 'Invoice', fieldname: 'name' },
					{ label: 'Status', fieldname: 'status', type: 'Badge' },
					{
						label: 'Date',
						fieldname: 'due_date',
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'short',
								day: 'numeric'
							}).format(new Date(value));
						}
					},
					{ label: 'Total', fieldname: 'total', format: this.formatCurrency },
					{
						label: 'Amount Due',
						fieldname: 'amount_due',
						format: this.formatCurrency
					}
				],
				filters: {
					team: this.team,
					due_date: [
						'>=',
						dayjs().subtract(1, 'month').endOf('month').format('YYYY-MM-DD')
					],
					partner_customer: true
				}
			};
		}
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return userCurrency(value);
		}
	}
};
</script>
