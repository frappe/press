<template>
	<div class="space-y-5">
		<Card title="Billing Summary">
			<div v-if="!$resources.upcomingInvoice.loading">
				<div class="grid grid-cols-2 gap-4 mb-4">
					<div class="border rounded-md p-4">
						<div class="text-base mb-2">Current Billing Amount</div>
						<div class="text-2xl font-medium">
							{{ upcomingInvoice ? upcomingInvoice.formatted.total : '0.00' }}
						</div>
					</div>
					<div class="border rounded-md p-4">
						<div class="flex justify-between text-base">
							<div>Total Unpaid Amount</div>
							<Button
								@click="showPrepaidCreditsDialog = true"
								theme="gray"
								iconLeft="credit-card"
								>Pay</Button
							>
						</div>
						<div class="text-2xl font-medium">
							{{
								($account.team.currency == 'INR' ? '₹' : '$') +
								' ' +
								$resources.unpaidAmountDue.data
							}}
						</div>
					</div>
					<div class="border rounded-md p-4">
						<div class="flex justify-between text-base">
							<div>Account Balance</div>
							<Button
								@click="showPrepaidCreditsDialog = true"
								theme="gray"
								iconLeft="plus"
								>Add</Button
							>
						</div>
						<div class="text-2xl font-medium">
							{{ availableCredits }}
						</div>
					</div>

					<div class="border rounded-md p-4">
						<div class="flex justify-between text-base">
							<div>Payment Mode</div>
							<Button @click="showChangeModeDialog = true" theme="gray"
								>Change</Button
							>
						</div>
						<div class="text-2xl font-medium">
							{{ $account.team.payment_mode || 'Not set' }}
						</div>
					</div>
				</div>

				<a
					href="https://frappecloud.com/payment-options"
					target="_blank"
					class="text-sm text-gray-700 underline"
				>
					Alternative Payment Options
				</a>
				<ErrorMessage
					:message="$resources.upcomingInvoice.error"
					class="mt-3"
				/>
			</div>

			<div class="py-20 text-center" v-if="loading">
				<Button :loading="true" loadingText="Loading" />
			</div>

			<ChangePaymentModeDialog v-model="showChangeModeDialog" />

			<PrepaidCreditsDialog
				v-if="showPrepaidCreditsDialog"
				v-model:show="showPrepaidCreditsDialog"
				:minimumAmount="Math.ceil(minimumAmount)"
				@success="
					() => {
						$resources.upcomingInvoice.reload();
						showPrepaidCreditsDialog = false;
					}
				"
			/>
		</Card>
		<UpcomingInvoiceSummary
			:invoice-doc="upcomingInvoice"
			v-if="upcomingInvoice?.items.length"
		/>
	</div>
</template>
<script>
import PlanIcon from '@/components/PlanIcon.vue';
import UpcomingInvoiceSummary from './UpcomingInvoiceSummary.vue';
import { defineAsyncComponent } from 'vue';
import InvoiceUsageTable from '@/components/InvoiceUsageTable.vue';

export default {
	name: 'BillingSummary',
	components: {
		InvoiceUsageTable,
		PlanIcon,
		UpcomingInvoiceSummary,
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('@/components/PrepaidCreditsDialog.vue')
		),
		ChangePaymentModeDialog: defineAsyncComponent(() =>
			import('@/components/ChangePaymentModeDialog.vue')
		)
	},
	resources: {
		upcomingInvoice: { url: 'press.api.billing.upcoming_invoice', auto: true },
		availablePartnerCredits() {
			return {
				url: 'press.api.billing.get_partner_credits'
			};
		},
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
			showChangeModeDialog: false
		};
	},
	mounted() {
		this.$socket.on('balance_updated', () =>
			this.$resources.upcomingInvoice.reload()
		);

		if (this.$account.team.payment_mode === 'Partner Credits') {
			this.$resources.availablePartnerCredits.submit();
		}
	},
	unmounted() {
		this.$socket.off('balance_updated');
	},
	computed: {
		cardBrand() {
			return {
				'master-card': defineAsyncComponent(() =>
					import('@/components/icons/cards/MasterCard.vue')
				),
				visa: defineAsyncComponent(() =>
					import('@/components/icons/cards/Visa.vue')
				),
				amex: defineAsyncComponent(() =>
					import('@/components/icons/cards/Amex.vue')
				),
				jcb: defineAsyncComponent(() =>
					import('@/components/icons/cards/JCB.vue')
				),
				generic: defineAsyncComponent(() =>
					import('@/components/icons/cards/Generic.vue')
				),
				'union-pay': defineAsyncComponent(() =>
					import('@/components/icons/cards/UnionPay.vue')
				)
			};
		},
		minimumAmount() {
			const unpaidAmount = this.$resources.unpaidAmountDue.data;
			const minimumDefault = $account.team.currency == 'INR' ? 800 : 10;

			return unpaidAmount && unpaidAmount > minimumDefault
				? unpaidAmount
				: minimumDefault;
		},
		upcomingInvoice() {
			return this.$resources.upcomingInvoice.data?.upcoming_invoice;
		},
		availableCredits() {
			if (this.$account.team.payment_mode === 'Partner Credits') {
				return this.$resources.availablePartnerCredits.data;
			}

			return this.$resources.upcomingInvoice.data?.available_credits;
		},
		paymentDate() {
			if (!this.upcomingInvoice) {
				return '';
			}
			let endDate = this.$date(this.upcomingInvoice.period_end);
			return endDate.toLocaleString({
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
		},
		paymentModeDescription() {
			let payment_mode = this.$account.team.payment_mode;
			let balance = this.$account.balance;
			if (payment_mode === 'Card') {
				if (!this.upcomingInvoice || balance <= 0) {
					return `Your card will be charged on ${this.paymentDate}.`;
				} else if (balance >= this.upcomingInvoice.total) {
					return `Your account balance will be charged on ${this.paymentDate}.`;
				} else if (balance > 0) {
					return `Your account balance will be charged and then the remaining balance will be charged from your card on ${this.paymentDate}.`;
				} else {
					return `Your card will be charged on ${this.paymentDate}.`;
				}
			}
			if (payment_mode === 'Prepaid Credits') {
				return `You will be charged from your account balance on ${this.paymentDate}.`;
			}

			if (payment_mode === 'Partner Credits') {
				return `You will be charged from your Partner Credits on ${this.paymentDate}.`;
			}
			return '';
		},
		loading() {
			return this.$resources.upcomingInvoice.loading;
		}
	},
	methods: {
		dateShort(date) {
			return this.$date(date).toLocaleString({
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
		}
	}
};
</script>
