<template>
	<div class="p-5">
		<div v-if="!$resources.upcomingInvoice.loading">
			<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between">
						<div class="text-sm text-gray-700">Current Billing Amount</div>
						<Button @click="showUpcomingInvoiceDialog = true"> Details </Button>
					</div>
					<div class="text-lg font-medium">
						{{ upcomingInvoice ? upcomingInvoice.formatted.total : '0.00' }}
					</div>
				</div>
				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between text-sm text-gray-700">
						<div>Unpaid Amount</div>
						<Button
							:disabled="Boolean($resources.unpaidAmountDue.data == 0)"
							@click="
								showPrepaidCreditsDialog = true;
								title = 'Pay your unpaid amount';
							"
							theme="gray"
							iconLeft="credit-card"
						>
							Pay
						</Button>
					</div>
					<div class="text-lg font-medium">
						{{
							($team?.doc?.currency == 'INR' ? '₹' : '$') +
							' ' +
							Math.ceil($resources.unpaidAmountDue.data)
						}}
					</div>
				</div>
				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between text-sm text-gray-700">
						<div>Credits Available</div>
						<Button
							@click="
								() => {
									if (!$team.doc?.billing_details?.name) {
										showBillingDetailsDialog = true;
										showMessage = true;
										return;
									}
									showPrepaidCreditsDialog = true;
								}
							"
							theme="gray"
							iconLeft="plus"
							>Add</Button
						>
					</div>
					<div class="text-lg font-medium">
						{{ availableCredits }}
					</div>
				</div>

				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between text-sm text-gray-700">
						<div>Payment Mode</div>
						<Button @click="showChangeModeDialog = true"> Change </Button>
					</div>
					<div class="text-lg font-medium">
						{{ $team?.doc?.payment_mode || 'Not set' }}
					</div>
					<div class="flex items-center gap-2">
						<p class="text-sm text-gray-600">
							{{ paymentModeDescription }}
						</p>
					</div>
				</div>
				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between text-sm text-gray-700">
						<div>Billing Details</div>
						<Button @click="showBillingDetailsDialog = true"> Update </Button>
					</div>
					<div class="overflow-hidden text-base leading-5">
						<span v-if="$team?.doc?.billing_details">
							{{ billingDetailsSummary }}
						</span>
						<span v-else class="font-normal text-gray-600">Not set</span>
					</div>
				</div>
				<div class="flex flex-col gap-2 rounded-md border p-4">
					<div class="flex items-center justify-between text-sm text-gray-700">
						<div>Payment Method</div>
						<Button @click="showAddCardDialog = true">
							{{ $team?.doc?.payment_method ? 'Change' : 'Add' }}
						</Button>
					</div>
					<div class="overflow-hidden text-ellipsis text-base font-medium">
						<div v-if="$team?.doc?.payment_method">
							{{ $team.doc.payment_method.name_on_card }}
							<span class="text-gray-500">••••</span>
							{{ $team.doc.payment_method.last_4 }}
							&middot;
							<span class="font-normal text-gray-600">
								Expiry {{ $team.doc.payment_method.expiry_month }}/{{
									$team.doc.payment_method.expiry_year
								}}
							</span>
						</div>

						<span v-else class="font-normal text-gray-600">Not set</span>
					</div>
				</div>
			</div>

			<div class="mt-1">
				<a
					href="https://frappecloud.com/payment-options"
					target="_blank"
					class="text-sm text-gray-700 underline"
				>
					Alternative Payment Options
				</a>
			</div>
		</div>

		<div class="py-20 text-center" v-if="$resources.upcomingInvoice.loading">
			<Button :loading="true" loadingText="Loading" />
		</div>

		<ChangePaymentModeDialog2 v-model="showChangeModeDialog" />

		<BuyPrepaidCreditsDialog
			:title="title"
			v-if="showPrepaidCreditsDialog"
			v-model="showPrepaidCreditsDialog"
			:minimumAmount="minimumAmount"
			@success="
				() => {
					$resources.upcomingInvoice.reload();
					showPrepaidCreditsDialog = false;
				}
			"
		/>

		<UpdateBillingDetails
			v-model="showBillingDetailsDialog"
			:message="
				showMessage ? 'Please update your billing details to add credits' : ''
			"
			@updated="
				showBillingDetailsDialog = false
				// $resources.billingDetails.reload();
			"
		/>

		<StripeCardDialog v-model="showAddCardDialog" />

		<Dialog
			v-if="upcomingInvoice?.name"
			v-model="showUpcomingInvoiceDialog"
			:options="{ title: 'Total usage for this month', size: '3xl' }"
		>
			<template #body-content>
				<InvoiceTable :invoiceId="upcomingInvoice.name" />
			</template>
		</Dialog>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import InvoiceTable from '../components/InvoiceTable.vue';
import UpdateBillingDetails from '../components/UpdateBillingDetails.vue';

export default {
	name: 'BillingOverview',
	components: {
		InvoiceTable,
		UpdateBillingDetails,
		ChangePaymentModeDialog2: defineAsyncComponent(() =>
			import('../components/ChangePaymentModeDialog.vue')
		),
		BuyPrepaidCreditsDialog: defineAsyncComponent(() =>
			import('../components/BuyPrepaidCreditsDialog.vue')
		),
		StripeCardDialog: defineAsyncComponent(() =>
			import('../components/StripeCardDialog.vue')
		)
	},
	resources: {
		upcomingInvoice: { url: 'press.api.billing.upcoming_invoice', auto: true },
		unpaidAmountDue() {
			return {
				url: 'press.api.billing.total_unpaid_amount',
				auto: true
			};
		}
	},
	data() {
		return {
			showPrepaidCreditsDialog: false,
			showChangeModeDialog: false,
			showBillingDetailsDialog: false,
			showAddCardDialog: false,
			showUpcomingInvoiceDialog: false,
			title: 'Add credits to your account',
			showMessage: false
		};
	},
	mounted() {
		this.$socket.on('balance_updated', () =>
			this.$resources.upcomingInvoice.reload()
		);
	},
	beforeUnmount() {
		this.$socket.off('balance_updated');
	},
	computed: {
		minimumAmount() {
			const unpaidAmount = this.$resources.unpaidAmountDue.data;
			const minimumDefault = this.$team?.doc?.currency == 'INR' ? 410 : 5;

			return Math.ceil(
				unpaidAmount && unpaidAmount > 0 ? unpaidAmount : minimumDefault
			);
		},
		upcomingInvoice() {
			return this.$resources.upcomingInvoice.data?.upcoming_invoice;
		},
		availableCredits() {
			return this.$resources.upcomingInvoice.data?.available_credits;
		},
		billingDetailsSummary() {
			const billingDetails = this.$team?.doc?.billing_details;
			if (!billingDetails) {
				return '';
			}

			const {
				billing_name,
				address_line1,
				country,
				city,
				state,
				pincode,
				gstin
			} = billingDetails;

			return [billing_name, address_line1, city, state, country, pincode, gstin]
				.filter(Boolean)
				.join(', ');
		},
		paymentModeDescription() {
			return {
				Card: `Your card will be charged for monthly subscription`,
				'Prepaid Credits': `You will be charged from your account balance for monthly subscription`,
				'Paid By Partner': `Your partner will be charged for monthly subscription`
			}[this.$team?.doc?.payment_mode];
		}
	}
};
</script>
