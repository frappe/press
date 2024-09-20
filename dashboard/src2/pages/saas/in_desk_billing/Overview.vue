<template>
	<div class="pt-5">
		<div v-if="!$resources.upcomingInvoice.loading">
			<!-- Current plan -->
			<div class="rounded-md border p-4">
				<div class="flex items-start justify-between">
					<div>
						<div class="text-lg font-medium">Current Plan</div>
						<div class="mt-0.5 text-sm text-gray-700">
							{{
								isSupportIncluded ? 'Support Included' : 'Support Not Included'
							}}
						</div>
					</div>
					<!-- <Button @click="showUpcomingInvoiceDialog = true"> Details </Button> -->
					<p class="inline-block text-gray-700">
						<span class="text-lg font-bold text-black">{{
							currentPlanPricing
						}}</span>
						/ month
					</p>
				</div>
				<div class="mt-2 flex justify-end">
					<Button
						variant="solid"
						theme="gray"
						@click="showSitePlanChangeDialog = true"
						>Change Plan</Button
					>
				</div>
			</div>
			<div class="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2">
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
						<Button
							v-if="Math.ceil($resources.unpaidAmountDue.data)"
							@click="openInvoicePage"
							theme="gray"
							>View Invoice</Button
						>
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

		<!-- Change plan dialog -->
		<SitePlanChangeDialog v-model="showSitePlanChangeDialog" />
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'BillingOverview',
	inject: ['team', 'site'],
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
		),
		SitePlanChangeDialog: defineAsyncComponent(() =>
			import('../../../components/in_desk_checkout/SitePlanChangeDialog.vue')
		)
	},
	mounted() {
		window.addEventListener('message', this.onMessageHandler);
		setTimeout(() => {
			if (window.posthog?.__loaded) {
				try {
					window.posthog.identify(this.team?.data?.user, {
						app: 'fc_in_desk_billing',
						page: 'billing_overview'
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
	data() {
		return {
			showPrepaidCreditsDialog: false,
			showChangeModeDialog: false,
			showBillingDetailsDialog: false,
			showAddCardDialog: false,
			showUpcomingInvoiceDialog: false,
			showSitePlanChangeDialog: false
		};
	},
	watch: {
		showPrepaidCreditsDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		},
		showChangeModeDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		},
		showBillingDetailsDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		},
		showAddCardDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		},
		showUpcomingInvoiceDialog(value) {
			this.triggerEventToParent(value ? 'modal:show' : 'modal:hide');
		}
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
			const minimumDefault = this.team?.data?.currency == 'INR' ? 410 : 5;

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
		},
		currentPlanPricing() {
			if (!this.site?.data || !this.team?.data) return '';
			return this.$format.currency(
				this.team?.data?.currency == 'INR'
					? this.site?.data?.plan?.price_inr
					: this.site?.data?.plan?.price_usd,
				this.team?.data?.currency,
				0
			);
		},
		isSupportIncluded() {
			if (!this.site?.data || !this.team?.data) return false;
			return this.site?.data?.plan?.support_included;
		}
	},
	methods: {
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
				this.showPrepaidCreditsDialog = false;
				this.showChangeModeDialog = false;
				this.showBillingDetailsDialog = false;
				this.showAddCardDialog = false;
				this.showUpcomingInvoiceDialog = false;
			}
		},
		openInvoicePage() {
			this.$router.push({
				name: 'IntegratedBillingInvoices',
				params: {
					accessToken: this.$route.params.accessToken
				}
			});
		}
	}
};
</script>
