<template>
	<div class="p-5">
		<ObjectList :options="options" />
		<Dialog
			v-model="invoiceDialog"
			:options="{ size: '3xl', title: showInvoice?.name }"
		>
			<template #body-content>
				<template v-if="showInvoice">
					<div
						v-if="showInvoice.status === 'Empty'"
						class="text-base text-gray-600"
					>
						Nothing to show
					</div>
					<InvoiceTable v-else :invoiceId="showInvoice.name" />
				</template>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
import InvoiceTable from '../components/InvoiceTable.vue';
import { userCurrency } from '../utils/format';
import { icon } from '../utils/components';

export default {
	name: 'BillingInvoices',
	props: ['tab'],
	components: {
		ObjectList,
		InvoiceTable
	},
	data() {
		return {
			invoiceDialog: false,
			showInvoice: null
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
						label: 'Amount Paid',
						fieldname: 'amount_paid',
						format: this.formatCurrency
					},
					{
						label: 'Amount Due',
						fieldname: 'amount_due',
						format: this.formatCurrency
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						Button({ row }) {
							if (row.invoice_pdf) {
								return {
									label: 'Download Invoice',
									slots: {
										prefix: icon('download')
									},
									onClick: () => {
										window.open(row.invoice_pdf);
									}
								};
							}
							if (row.status !== 'Paid' && row.amount_due > 0) {
								return {
									label: 'Pay Now',
									slots: {
										prefix: icon('external-link')
									},
									onClick: () => {
										window.open(
											`/api/method/run_doc_method?dt=Invoice&dn=${row.name}&method=stripe_payment_url`
										);
									}
								};
							}
						}
					}
				],
				orderBy: 'due_date desc',
				onRowClick: row => {
					this.showInvoice = row;
					this.invoiceDialog = true;
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
