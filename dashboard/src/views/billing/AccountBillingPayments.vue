<template>
	<Card
		title="Billing history"
		:subtitle="subtitle"
		v-if="!invoiceName && $resources.pastInvoices.data"
	>
		<template #actions>
			<Dropdown :options="dropdownItems">
				<Button icon-right="filter">Filter</Button>
			</Dropdown>
		</template>
		<div
			class="max-h-96 divide-y"
			v-if="$resources.pastInvoices.data && $resources.pastInvoices.data.length"
		>
			<div
				class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600 md:grid-cols-6"
			>
				<span>Date</span>
				<span class="hidden md:inline">Description</span>
				<span class="hidden md:inline">Amount</span>
				<span>Status</span>
				<span class="hidden md:inline">Payment Date</span>
				<span></span>
			</div>
			<div
				:key="invoice.name"
				v-for="invoice in $resources.pastInvoices.data"
				class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900 md:grid-cols-6"
			>
				<div>
					<div>
						{{
							$date(invoice.date).toLocaleString({
								month: 'long',
								day: 'numeric',
								year: 'numeric'
							})
						}}
					</div>
					<div class="mt-2 md:hidden">
						{{ invoice.formatted_total }}
					</div>
				</div>
				<span class="hidden md:inline">
					<Link
						v-if="invoice.type == 'Subscription'"
						:to="'/billing/' + invoice.name"
					>
						Invoice for
						{{
							$date(invoice.period_end).toLocaleString({
								month: 'long',
								year: 'numeric'
							})
						}}
					</Link>
					<span v-if="invoice.type === 'Prepaid Credits'">
						Prepaid Credits
					</span>
					<span v-if="invoice.type === 'Transferred Credits'">
						Transferred Credits
					</span>
				</span>
				<span class="hidden md:inline">{{ invoice.formatted_total }}</span>
				<span>
					<Badge v-bind="getStatusBadgeProps(invoice)">
						{{ invoice.status }}
					</Badge>
				</span>
				<span class="hidden md:inline">
					<span
						v-if="
							invoice.status == 'Paid' && invoice.type !== 'Prepaid Credits'
						"
					>
						{{
							$date(invoice.payment_date).toLocaleString({
								month: 'long',
								day: 'numeric',
								year: 'numeric'
							})
						}}
					</span>
				</span>
				<div class="flex items-center justify-end space-x-2">
					<Button
						v-if="invoice.invoice_pdf"
						icon-left="download"
						class="shrink-0"
						:link="invoice.invoice_pdf"
					>
						<span class="text-sm">Download Invoice</span>
					</Button>
					<Button
						v-if="invoice.status != 'Paid' && invoice.stripe_invoice_url"
						icon-left="external-link"
						class="shrink-0"
						:link="invoice.stripe_invoice_url"
					>
						<span class="text-sm">Pay Now</span>
					</Button>
				</div>
			</div>
		</div>
	</Card>
	<InvoiceUsageCard :invoice="invoiceName" v-else />
</template>
<script>
import InvoiceUsageCard from '@/components/InvoiceUsageCard.vue';
export default {
	name: 'AccountBillingPayments',
	props: ['invoiceName'],
	components: {
		InvoiceUsageCard
	},
	data() {
		return {
			dropdownItems: [
				{
					label: 'All Invoices',
					handler: () => this.$resources.pastInvoices.submit()
				},
				{
					label: 'Unpaid Invoices',
					handler: () =>
						this.$resources.pastInvoices.submit({ invoice_status: 'unpaid' })
				},
				{
					label: 'Paid Invoices',
					handler: () =>
						this.$resources.pastInvoices.submit({ invoice_status: 'paid' })
				}
			]
		};
	},
	resources: {
		pastInvoices: 'press.api.billing.invoices_and_payments'
	},
	computed: {
		subtitle() {
			if (
				this.$resources.pastInvoices.loading ||
				this.$resources.pastInvoices.data.length > 0
			) {
				return 'History of your invoice payments';
			}
			return 'No invoices have been generated yet';
		}
	},
	methods: {
		getStatusBadgeProps(invoice) {
			return {
				status: invoice.status,
				color: {
					Paid: 'green',
					Unpaid: 'yellow',
					'Invoice Created': 'blue'
				}[invoice.status]
			};
		}
	}
};
</script>
