<template>
	<div class="p-5">
		<div v-if="!$resources.upcomingInvoice.loading">
			<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
				<!-- Current billing amount -->
				<div class="rounded-md border p-4">
					<div class="flex items-center justify-between">
						<div class="mb-2 text-sm text-gray-700">Current Billing Amount</div>
						<Button @click="showUpcomingInvoiceDialog = true"> Details </Button>
					</div>
					<div class="text-lg font-medium">
						{{ upcomingInvoice ? upcomingInvoice.formatted.total : '0.00' }}
					</div>
				</div>
				<!-- Unpaid amount -->
				<div class="rounded-md border p-4">
					<div class="flex justify-between text-sm text-gray-700">
						<div class="mb-2">Unpaid Amount</div>
					</div>
					<div class="text-lg font-medium">
						{{
							(team?.data?.currency == 'INR' ? '₹' : '$') +
							' ' +
							Math.ceil($resources.unpaidAmountDue.data)
						}}
					</div>
				</div>
				<!-- Account Balance -->
				<div class="rounded-md border p-4">
					<div class="flex justify-between text-sm text-gray-700">
						<div class="mb-2">Account Balance</div>
						<Button
							@click="showPrepaidCreditsDialog = true"
							theme="gray"
							iconLeft="plus"
							>Add</Button
						>
					</div>
					<div class="text-lg font-medium">
						{{ availableCredits }}
					</div>
				</div>
				<!-- Payment Mode -->
				<div class="rounded-md border p-4">
					<div class="flex justify-between text-sm text-gray-700">
						<div class="mb-2">Payment Mode</div>
						<Button @click="showChangeModeDialog = true"> Change </Button>
					</div>
					<div class="text-lg font-medium">
						{{ team?.data?.payment_mode || 'Not set' }}
					</div>
				</div>
				<!-- Billing Details -->
				<div class="rounded-md border p-4">
					<div class="flex justify-between text-sm text-gray-700">
						<div class="mb-2">Billing Details</div>
						<Button @click="showBillingDetailsDialog = true"> Update </Button>
					</div>
					<div class="overflow-hidden text-ellipsis text-base font-medium">
						<span class="whitespace-nowrap" v-if="team?.data?.billing_details">
							{{ billingDetailsSummary }}
						</span>
						<span v-else class="font-normal text-gray-600">Not set</span>
					</div>
				</div>
				<!-- Payment Method -->
				<div class="rounded-md border p-4">
					<div class="flex justify-between text-sm text-gray-700">
						<div class="mb-2">Payment Method</div>
						<Button @click="showAddCardDialog = true">
							{{ team?.data?.payment_method ? 'Change' : 'Add' }}
						</Button>
					</div>
					<div class="overflow-hidden text-ellipsis text-base font-medium">
						<div v-if="team?.data?.payment_method">
							{{ team?.data?.payment_method.name_on_card }}
							<span class="text-gray-500">••••</span>
							{{ team?.data?.payment_method.last_4 }}
							&middot;
							<span class="font-normal text-gray-600">
								Expiry {{ team?.data?.payment_method.expiry_month }}/{{
									team?.data?.payment_method.expiry_year
								}}
							</span>
						</div>
						<span v-else class="font-normal text-gray-600">Not set</span>
					</div>
				</div>
			</div>
		</div>

		<div class="py-20 text-center" v-if="$resources.upcomingInvoice.loading">
			<Button :loading="true" loadingText="Loading" />
		</div>

		<!-- Upcoming Invoice Details -->
		<Dialog
			v-if="upcomingInvoice?.name"
			v-model="showUpcomingInvoiceDialog"
			:options="{ title: 'Total usage for this month', size: '3xl' }"
		>
			<template #body-content>
				<InvoiceTable :invoiceId="upcomingInvoice.name" />
			</template>
		</Dialog>

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
							$resources.upcomingInvoice.reload();
							showPrepaidCreditsDialog = false;
						}
					"
				/>
			</template>
		</Dialog>

		<!-- Add New Card Dialog -->
		<Dialog
			v-if="showAddCardDialog"
			v-model="showAddCardDialog"
			:options="{
				title: 'Add New Card'
			}"
		>
			<template #body-content>
				<StripeCard2
					@complete="
						() => {
							showAddCardDialog = false;
							this.team.reload();
						}
					"
				/>
			</template>
		</Dialog>

		<!-- Update Billing Details Form -->
		<Dialog
			v-if="showBillingDetailsDialog"
			v-model="showBillingDetailsDialog"
			:options="{ title: 'Update Billing Details' }"
		>
			<template #body-content>
				<UpdateAddressForm
					submitButtonText="Submit"
					:submitButtonWidthFull="true"
					@updated="
						() => {
							showBillingDetailsDialog = false;
							this.team.reload();
						}
					"
				/>
			</template>
		</Dialog>

		<!-- Change payment mode dialog -->
		<ChangePaymentModeDialog2 v-model="showChangeModeDialog" />
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'BillingOverview',
	inject: ['team'],
	components: {
		InvoiceTable: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/InvoiceTable.vue')
		),
		BuyPrepaidCreditsForm: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/BuyPrepaidCreditsForm.vue')
		),
		UpdateAddressForm: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/UpdateAddressForm.vue')
		),
		StripeCard2: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/StripeCard.vue')
		),
		ChangePaymentModeDialog2: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/ChangePaymentModeDialog.vue')
		)
	},
	data() {
		return {
			showPrepaidCreditsDialog: false,
			showChangeModeDialog: false,
			showBillingDetailsDialog: false,
			showAddCardDialog: false,
			showUpcomingInvoiceDialog: false
		};
	},
	resources: {
		upcomingInvoice: {
			url: 'press.saas.api.billing.upcoming_invoice',
			auto: true
		},
		unpaidAmountDue() {
			return {
				url: 'press.saas.api.billing.total_unpaid_amount',
				auto: true
			};
		}
	},
	computed: {
		minimumAmount() {
			const unpaidAmount = this.$resources.unpaidAmountDue.data;
			const minimumDefault = this.team?.data?.currency == 'INR' ? 800 : 10;

			return Math.ceil(
				unpaidAmount && unpaidAmount > minimumDefault
					? unpaidAmount
					: minimumDefault
			);
		},
		upcomingInvoice() {
			return this.$resources.upcomingInvoice.data?.upcoming_invoice;
		},
		availableCredits() {
			return this.$resources.upcomingInvoice.data?.available_credits;
		},
		billingDetailsSummary() {
			const billingDetails = this.team?.data?.billing_details;
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
		}
	}
};
</script>
