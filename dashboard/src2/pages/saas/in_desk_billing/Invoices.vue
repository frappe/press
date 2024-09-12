<template>
	<div class="pt-5">
		<ObjectList :options="invoiceList" />
		<Dialog
			v-model="showInvoiceDialog"
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

	<!-- Add Prepaid Credits Dialog -->
	<Dialog
		v-if="showPrepaidCreditsDialog"
		v-model="showPrepaidCreditsDialog"
		:options="{
			title: 'Add Prepaid Credit'
		}"
	>
		<template #body-content>
			<BuyPrepaidCreditsForm
				:minimumAmount="minimumAmount"
				@success="
					() => {
						showPrepaidCreditsDialog = false;
					}
				"
			/>
		</template>
	</Dialog>
</template>
<script>
import ObjectList from '../../../components/ObjectList.vue';
import { currency, date } from '../../../utils/format';
import { dayjsLocal } from '../../../utils/dayjs';
import { icon } from '../../../utils/components';
import { Button } from 'frappe-ui';
import InvoiceTable from '../../../components/in_desk_checkout/InvoiceTable.vue';
import { createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'IntegratedBillingInvoices',
	components: {
		ObjectList,
		InvoiceTable,
		BuyPrepaidCreditsForm: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/BuyPrepaidCreditsForm.vue')
		)
	},
	inject: ['team', 'site'],
	data() {
		return {
			showInvoiceDialog: false,
			showInvoice: null,
			showPrepaidCreditsDialog: false,
			minimumAmount: 0
		};
	},
	mounted() {
		window.addEventListener('message', this.onMessageHandler);
		setTimeout(() => {
			if (window.posthog?.__loaded) {
				try {
					window.posthog.identify(this.team?.data?.user, {
						app: 'fc_in_desk_billing',
						page: 'invoice_list'
					});
					if (!window.posthog.sessionRecordingStarted()) {
						window.posthog.startSessionRecording();
					}
				} catch (e) {
					console.error(e);
				}
			}
		}, 3000);
	},
	beforeUnmount() {
		window.removeEventListener('message', this.onMessageHandler);
	},
	watch: {
		showInvoiceDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		}
	},
	computed: {
		invoiceList() {
			return {
				resource() {
					return {
						url: 'press.saas.api.billing.get_invoices',
						initialData: [],
						auto: true
					};
				},
				columns: [
					{
						label: 'Invoice',
						fieldname: 'name',
						class: 'font-medium',
						format(value, row) {
							if (row.type == 'Subscription') {
								let end = dayjsLocal(row.period_end);
								return end.format('MMMM YYYY');
							}
							return 'Prepaid Credits';
						},
						width: 0.8
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						width: '150px'
					},
					{
						label: 'Date',
						fieldname: 'due_date',
						format(value, row) {
							if (row.type == 'Subscription') {
								let start = dayjsLocal(row.period_start);
								let end = dayjsLocal(row.period_end);
								let sameYear = start.year() === end.year();
								let formattedStart = sameYear
									? start.format('MMM D')
									: start.format('ll');
								return `${formattedStart} - ${end.format('ll')}`;
							}
							return date(value, 'll');
						}
					},
					{
						label: 'Total',
						fieldname: 'total',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6
					},
					{
						label: 'Amount Paid',
						fieldname: 'amount_paid',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6
					},
					{
						label: 'Amount Due',
						fieldname: 'amount_due',
						format: this.formatCurrency,
						align: 'right',
						width: 0.6
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
									onClick: e => {
										e.stopPropagation();
										fetch(
											'/api/method/press.saas.api.billing.download_invoice',
											{
												method: 'POST',
												headers: {
													'Content-Type': 'application/json',
													'X-Site-Access-Token': this.$route.params.accessToken
												},
												body: JSON.stringify({ name: row.name })
											}
										)
											.then(response => {
												if (!response.ok) {
													throw new Error(
														'Network response was not ok ' + response.statusText
													);
												}
												return response.blob();
											})
											.then(blob => {
												const url = window.URL.createObjectURL(blob);
												window.open(url, '_blank');
											})
											.catch(error => {
												console.error(
													'There was a problem with the fetch operation:',
													error
												);
											});
									}
								};
							}
							if (row.status === 'Unpaid' && row.amount_due > 0) {
								return {
									label: 'Pay Now',
									slots: {
										prefix: icon('external-link')
									},
									onClick: e => {
										if (row.stripe_invoice_id && row.payment_mode == 'Card') {
											this.openStripeInvoicePaymentPage(row.name);
										} else {
											this.showPrepaidCreditsDialog = true;
											this.minimumAmount = row.amount_due;
										}
										e.stopPropagation();
									}
								};
							}
						},
						prefix(row) {
							if (row.stripe_payment_failed && row.status !== 'Paid') {
								return h(Button, {
									variant: 'ghost',
									theme: 'red',
									icon: 'alert-circle',
									onClick(e) {
										e.stopPropagation();
									}
								});
							}
						}
					}
				],
				orderBy: 'due_date desc, creation desc',
				onRowClick: row => {
					this.showInvoice = row;
					this.showInvoiceDialog = true;
				}
			};
		}
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return currency(value, this.team?.data?.currency);
		},
		triggerEventToParent(eventName) {
			if (window?.parent) {
				try {
					window.parent.postMessage(
						eventName,
						`https://${this.site?.data?.name}`
					);
				} catch (e) {
					console.error('failed to send message to parent', e);
				}
			}
		},
		onMessageHandler(event) {
			if (event.data === 'backdrop_clicked') {
				this.showInvoiceDialog = false;
			}
		},
		openStripeInvoicePaymentPage(name) {
			let request = createResource({
				url: '/api/method/press.saas.api.billing.get_stripe_payment_url_for_invoice',
				params: {
					name
				},
				onSuccess: url => {
					if (url) {
						window.open(url, '_blank');
					} else {
						toast.error(
							'Failed to fetch Stripe Payment URL. Please try again later.'
						);
					}
				},
				onError: () => {
					toast.error(
						'Failed to fetch Stripe Payment URL. Please try again later.'
					);
				}
			});
			request.submit();
		}
	}
};
</script>
