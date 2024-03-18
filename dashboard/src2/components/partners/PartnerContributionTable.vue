<template>
	<div>
		<ObjectList :options="options" />
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
import { currency, userCurrency } from '../../utils/format';
import dayjs from '../../utils/dayjs';

export default {
	name: 'PartnerContributionTable',
	props: ['partnerEmail'],
	components: {
		ObjectList
	},
	data() {
		return {
			email: this.partnerEmail
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Invoice',
				fields: ['type'],
				columns: [
					{
						label: 'Customer',
						fieldname: 'customer_name'
					},
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
					{
						label: 'Currency',
						fieldname: 'currency'
					},
					{
						label: 'Total',
						fieldname: 'total',
						format(value, columns) {
							if (value === 0) {
								return '';
							}
							return currency(value, columns.currency);
						}
					},
					{
						label: 'Partner Total',
						fieldname: 'partner_total',
						format(value) {
							return userCurrency(value);
						}
					}
				],
				filters: {
					partner_email: this.email,
					due_date: ['>=', dayjs().endOf('month').format('YYYY-MM-DD')],
					partner_contribution: true
				}
			};
		}
	}
};
</script>
