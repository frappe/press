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
		<BuyPrepaidCreditsDialog
			v-if="showBuyPrepaidCreditsDialog"
			v-model="showBuyPrepaidCreditsDialog"
			:minimumAmount="minimumAmount"
			@success="
				() => {
					showBuyPrepaidCreditsDialog = false;
				}
			"
		/>
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
import InvoiceTable from '../components/InvoiceTable.vue';
import { userCurrency } from '../utils/format';
import { icon } from '../utils/components';
import BuyPrepaidCreditsDialog from '../components/BuyPrepaidCreditsDialog.vue';

export default {
	name: 'BillingInvoices',
	props: ['tab'],
	components: {
		ObjectList,
		InvoiceTable,
		BuyPrepaidCreditsDialog
	},
	data() {
		return {
			invoiceDialog: false,
			showInvoice: null,
			showBuyPrepaidCreditsDialog: false,
			minimumAmount: 0
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Invoice',
				fields: ['type', 'invoice_pdf', 'payment_mode', 'stripe_invoice_url'],
				filterControls() {
					return [
						{
							type: 'select',
							label: 'Status',
							class: 'w-36',
							fieldname: 'status',
							options: [
								'',
								'Draft',
								'Invoice Created',
								'Unpaid',
								'Paid',
								'Refunded',
								'Uncollectible',
								'Collected',
								'Empty'
							]
						}
					];
				},
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
						format: this.formatCurrency,
						width: 0.7
					},
					{
						label: 'Amount Due',
						fieldname: 'amount_due',
						format: this.formatCurrency,
						width: 0.7
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						Button: ({ row }) => {
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
										if (row.stripe_invoice_url && row.payment_mode == 'Card') {
											window.open(
												`/api/method/press.api.client.run_doc_method?dt=Invoice&dn=${row.name}&method=stripe_payment_url`
											);
										} else {
											this.showBuyPrepaidCreditsDialog = true;
											this.minimumAmount = row.amount_due;
										}
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
