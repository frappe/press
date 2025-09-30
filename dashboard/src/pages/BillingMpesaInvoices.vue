<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>

<script>
import { frappeRequest } from 'frappe-ui';
import ObjectList from '../components/ObjectList.vue';
import { icon } from '../utils/components';

export default {
	name: 'BillingMpesaInvoices',
	data() {
		return {
			invoices: [],
			loading: false,
			errorMessage: null,
		};
	},
	components: {
		ObjectList,
	},
	methods: {
		async fetchInvoices() {
			this.loading = true;
			try {
				const response = await frappeRequest({
					url: '/api/method/press.api.regional_payments.mpesa.utils.display_invoices_by_partner',
					method: 'GET',
				});
				this.invoices = response;
			} catch (error) {
				this.errorMessage = `Failed to load invoices. ${error}`;
			} finally {
				this.loading = false;
			}
		},
		formatCurrency(value) {
			return new Intl.NumberFormat('en-US', {
				style: 'currency',
				currency: 'Ksh',
			}).format(value);
		},
	},
	computed: {
		options() {
			return {
				doctype: 'Mpesa Payment Record',
				fields: [
					'name',
					'posting_date',
					'amount',
					'local_invoice',
					'payment_partner',
					'amount_usd',
					'exchange_rate',
				],
				columns: [
					{
						label: 'Invoice Name',
						fieldname: 'name',
						width: 1,
					},
					{
						label: 'Date',
						fieldname: 'posting_date',
						width: 0.7,
					},
					{
						label: 'Amount',
						fieldname: 'amount',
						align: 'center',
						width: 0.6,
					},
					{
						label: 'Amount (USD)',
						fieldname: 'amount_usd',
						align: 'center',
						width: 0.6,
					},
					{
						label: 'Exchange Rate',
						fieldname: 'exchange_rate',
						align: 'center',
						width: 0.6,
					},
					{
						label: 'Payment Partner',
						fieldname: 'payment_partner',
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						Button: ({ row }) => {
							if (row.local_invoice) {
								return {
									label: 'Download Invoice',
									slots: {
										prefix: icon('download'),
									},
									onClick: () => {
										window.open(row.local_invoice);
									},
								};
							}
						},
					},
				],
				orderBy: 'posting_date desc',
			};
		},
	},
	mounted() {
		this.fetchInvoices();
	},
};
</script>
