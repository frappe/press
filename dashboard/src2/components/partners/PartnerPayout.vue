<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>

<script>
import ObjectList from '../ObjectList.vue';
import { currency } from '../../utils/format';
import { Button } from 'frappe-ui';
import { icon } from '../../utils/components';
import router from '../../router';

export default {
	components: { ObjectList, Button },
	data() {
		return {
			currency: 'USD',
			debugData: null,
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Partner Payment Payout',
				fields: ['type'],
				columns: [
					{ label: 'Payout ID', fieldname: 'name' },
					{
						label: 'Payment Gateway',
						fieldname: 'payment_gateway',
						format: (value) => value || 'N/A',
					},
					{
						label: 'Posting Date',
						fieldname: 'posting_date',
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'short',
								day: 'numeric',
							}).format(new Date(value));
						},
					},
					{
						label: 'Total Amount',
						fieldname: 'total_amount',
						format: (value) => this.formatCurrency(value),
					},
					{
						label: 'Commission',
						fieldname: 'commission',
						format: (value) => this.formatCurrency(value),
					},
					{
						label: 'Net Amount',
						fieldname: 'net_amount',
						format: (value) => this.formatCurrency(value),
					},
				],

				filters: {
					docstatus: 1,
					partner: this.$team.doc.name,
				},
				primaryAction() {
					return {
						label: 'New Payout',
						variant: 'solid',

						slots: {
							prefix: icon('plus'),
						},
						onClick() {
							router.push({ name: 'PartnerNewPayout' });
						},
					};
				},
				orderBy: 'posting_date desc',
				emptyStateText: 'No payouts found',
			};
		},
	},
	methods: {
		formatCurrency(value) {
			if (value === 0 || value === null || value === undefined) {
				return 'N/A';
			}
			return currency(value, this.currency);
		},
	},
};
</script>
