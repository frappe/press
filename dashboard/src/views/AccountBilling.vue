<template>
	<div class="space-y-10">
		<Section
			title="Subscription"
			description="This is the amount so far based on the usage of your sites"
		>
			<SectionCard>
				<div
					class="px-6 py-3 text-base text-gray-800"
					v-if="$resources.billingDetails.loading"
				>
					Fetching billing information...
				</div>
				<DescriptionList class="px-6 py-4" :items="subscriptionItems" />
				<div
					class="px-6 pb-4"
					v-if="!$resources.billingDetails.loading && !paymentMethodAdded"
				>
					<Button type="primary" route="/welcome">
						Add Billing Information
					</Button>
				</div>
				<div class="px-6 pb-2 space-x-2">
					<Button
						v-if="$account.team.enable_prepaid_credits"
						@click="showPrepaidCreditsDialog = true"
					>
						Add Balance
					</Button>
					<Button
						@click="showTransferCreditsDialog = true"
						v-if="$account.team.erpnext_partner"
					>
						Transfer Credits from ERPNext.com
					</Button>
				</div>
			</SectionCard>
		</Section>

		<TransferCreditsDialog
			v-if="showTransferCreditsDialog"
			:show.sync="showTransferCreditsDialog"
			@success="$resources.billingDetails.reload()"
		/>

		<PrepaidCreditsDialog
			v-if="showPrepaidCreditsDialog"
			:show.sync="showPrepaidCreditsDialog"
			:minimum-amount="$account.team.currency == 'INR' ? 800 : 10"
			@success="$resources.billingDetails.reload()"
		/>

		<Section
			v-if="pastInvoices.length"
			title="Past Invoices"
			description="History of your invoice payments"
		>
			<SectionCard>
				<div
					class="grid items-start grid-cols-5 px-6 py-4 hover:bg-gray-50"
					v-for="invoice in pastInvoices"
					:key="invoice.name"
				>
					<div class="col-span-2">
						<div class="text-base font-semibold">
							{{ invoicePeriod(invoice) }}
						</div>
						<div class="mt-2 text-base">{{ invoice.formatted_total }}</div>
					</div>
					<div class="text-right">
						<Badge v-if="invoice.status == 'Paid'" color="green">
							Paid
						</Badge>
						<Badge v-if="invoice.status == 'Unpaid'" color="orange">
							Unpaid
						</Badge>
						<Badge v-else-if="invoice.status == 'Invoice Created'" color="blue">
							Created
						</Badge>
					</div>
					<div class="flex flex-col items-end col-span-2 space-y-2">
						<Button
							v-if="['Unpaid', 'Paid'].includes(invoice.status)"
							@click.prevent="showUsageForInvoice = invoice.name"
						>
							Details
						</Button>
						<a
							v-if="invoice.status != 'Paid' && invoice.stripe_invoice_url"
							class="flex items-center justify-center text-base text-blue-500"
							:href="invoice.stripe_invoice_url"
							target="_blank"
						>
							Pay Now
							<FeatherIcon name="arrow-right" class="w-4 h-4 ml-2" />
						</a>
					</div>
				</div>
			</SectionCard>
			<InvoiceUsage :invoice.sync="showUsageForInvoice" />
		</Section>
		<Section
			v-if="!$resources.billingDetails.loading"
			title="Billing Details"
			description="Your billing address is shown in monthly invoice"
		>
			<SectionCard>
				<div class="flex items-center justify-between px-6 py-2">
					<span class="text-base">
						{{ billingDetails.data.billing_address }}
					</span>
					<Button @click="editAddress = true">Edit Address</Button>
				</div>
				<UpdateBillingAddress
					v-if="editAddress"
					@updated="
						editAddress = false;
						billingDetails.reload();
					"
				/>
			</SectionCard>
		</Section>
		<Section
			v-if="paymentMethods.data && paymentMethods.data.length > 0"
			title="Payment Methods"
			description="Cards you have added for automatic billing"
		>
			<SectionCard>
				<div
					class="grid items-start grid-cols-5 px-6 py-4 text-base hover:bg-gray-50"
					v-for="paymentMethod in paymentMethods.data"
					:key="paymentMethod.name"
				>
					<div class="col-span-2">
						<div class="flex items-baseline space-x-2">
							<div class="font-semibold">•••• {{ paymentMethod.last_4 }}</div>
							<Badge v-if="paymentMethod.is_default" color="blue">
								Default
							</Badge>
						</div>
						<div class="text-sm text-gray-600">
							Expires
							{{ paymentMethod.expiry_month }} /
							{{ paymentMethod.expiry_year }}
						</div>
					</div>
					<div class="col-span-2">
						{{ paymentMethod.name_on_card }}
					</div>
					<div class="text-sm text-right text-gray-600 whitespace-no-wrap">
						Added on
						{{
							$date(paymentMethod.creation).toLocaleString({
								month: 'short',
								day: 'numeric'
							})
						}}
					</div>
				</div>
				<div class="px-6 py-4">
					<Button @click="showStripeCardDialog = true">
						Add Payment Method
					</Button>
					<Dialog
						title="Add Billing Information"
						v-model="showStripeCardDialog"
					>
						<StripeCard
							class="mb-1"
							v-if="showStripeCardDialog"
							@complete="onCardAdd"
						/>
					</Dialog>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
import DescriptionList from '@/components/DescriptionList';
import { DateTime } from 'luxon';

export default {
	name: 'AccountBilling',
	components: {
		StripeCard,
		DescriptionList,
		TransferCreditsDialog: () => import('@/components/TransferCreditsDialog'),
		PrepaidCreditsDialog: () => import('@/components/PrepaidCreditsDialog'),
		UpdateBillingAddress: () => import('@/components/UpdateBillingAddress'),
		InvoiceUsage: () => import('@/components/InvoiceUsage')
	},
	resources: {
		billingDetails: {
			method: 'press.api.billing.info',
			default: {
				upcoming_invoice: null,
				available_credits: null,
				billing_address: null,
				past_invoices: []
			},
			auto: true
		},
		paymentMethods: {
			method: 'press.api.billing.get_payment_methods',
			auto: true
		}
	},
	data() {
		return {
			showStripeCardDialog: false,
			showTransferCreditsDialog: false,
			showPrepaidCreditsDialog: false,
			showUsageForInvoice: null,
			editAddress: false
		};
	},
	mounted() {
		this.$socket.on('balance_updated', () => {
			this.$resources.billingDetails.reload();
		});
	},
	destroyed() {
		this.$socket.off('balance_updated');
	},
	computed: {
		paymentMethodAdded() {
			return this.billingDetails.data?.payment_method;
		},
		upcomingInvoice() {
			return this.billingDetails.data?.upcoming_invoice;
		},
		pastInvoices() {
			return this.billingDetails.data?.past_invoices || [];
		},
		availableCredits() {
			return this.billingDetails.data?.available_credits;
		},
		subscriptionItems() {
			return [
				this.upcomingInvoice
					? {
							label: `Usage since ${this.$date(
								this.upcomingInvoice.period_start
							).toLocaleString({
								month: 'long',
								day: 'numeric'
							})}`,
							value: this.upcomingInvoice.formatted_total
					  }
					: null,
				this.upcomingInvoice?.due_date
					? {
							label: 'Next Invoice Date',
							value: this.$date(this.upcomingInvoice.due_date).toLocaleString({
								month: 'long',
								day: 'numeric',
								year: 'numeric'
							})
					  }
					: null,
				this.upcomingInvoice?.customer_email
					? {
							label: 'Billed To',
							value: this.upcomingInvoice.customer_email
					  }
					: null,
				{
					label: 'Account Balance',
					value: this.availableCredits || 0
				}
			].filter(Boolean);
		}
	},
	methods: {
		onCardAdd() {
			this.showStripeCardDialog = false;
			this.$resources.paymentMethods.reload();
		},
		invoicePeriod(invoice) {
			if (!invoice.period_start || !invoice.period_end) {
				return DateTime.fromSQL(invoice.due_date).toLocaleString({
					month: 'long',
					day: 'numeric',
					year: 'numeric'
				});
			}
			let periodStart = DateTime.fromSQL(invoice.period_start);
			let periodEnd = DateTime.fromSQL(invoice.period_end);
			let start = periodStart.toLocaleString({
				month: 'short',
				day: 'numeric'
			});
			let end = periodEnd.toLocaleString({ month: 'short', day: 'numeric' });
			return `${start} - ${end} ${periodEnd.year}`;
		}
	}
};
</script>
