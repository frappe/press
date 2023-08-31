<template>
	<div class="space-y-5">
		<Card title="Billing summary">
			<div v-if="!$resources.upcomingInvoice.loading">
				<div class="space-y-2">
					<div class="grid grid-cols-3 items-center py-1.5">
						<label class="text-base text-gray-700">
							Current billing amount
						</label>
						<div class="col-span-2 text-lg font-semibold">
							{{ upcomingInvoice ? upcomingInvoice.formatted.total : '0.00' }}
						</div>
					</div>
					<div class="grid grid-cols-3 items-center py-1.5">
						<label class="text-base text-gray-700">Current billing cycle</label>
						<div
							class="col-span-2 text-base text-gray-900"
							v-if="upcomingInvoice"
						>
							{{ dateShort(upcomingInvoice.period_start) }}
							→
							{{ dateShort(upcomingInvoice.period_end) }}
						</div>
					</div>
					<div class="grid grid-cols-3 items-center">
						<label class="text-base text-gray-700"> Account balance </label>
						<div class="text-base">
							{{ availableCredits }}
						</div>
						<div class="text-right">
							<Button
								class="ml-2"
								@click="showPrepaidCreditsDialog = true"
								theme="gray"
							>
								Add money
							</Button>
						</div>
					</div>
					<div class="grid grid-cols-3 items-start">
						<label class="pt-1.5 text-base text-gray-700"> Payment mode </label>
						<div class="pt-1.5 text-base">
							<div>
								{{ $account.team.payment_mode || 'Not set' }}
							</div>
							<div class="mt-1 text-gray-600 empty:hidden">
								{{ paymentModeDescription }}
							</div>
						</div>
						<div class="text-right">
							<Button @click="showChangeModeDialog = true">
								Change Payment Mode
							</Button>
						</div>
					</div>
				</div>

				<ErrorMessage
					v-if="$resourceErrors"
					:message="$resourceErrors"
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
				:minimum-amount="minimumAmount"
				@success="
					() => {
						$resources.upcomingInvoice.reload();
						showPrepaidCreditsDialog = false;
					}
				"
			/>
		</Card>
		<AccountBillingUpcomingInvoice
			:invoice-doc="upcomingInvoice"
			v-if="upcomingInvoice?.items.length"
		/>
	</div>
</template>
<script>
import PlanIcon from '@/components/PlanIcon.vue';
import AccountBillingUpcomingInvoice from './AccountBillingUpcomingInvoice.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'AccountBillingUsage',
	components: {
		PlanIcon,
		AccountBillingUpcomingInvoice,
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
