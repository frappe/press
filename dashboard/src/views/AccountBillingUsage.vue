<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<Card
			title="Usage"
			subtitle="Amount so far based on the usage of your sites"
		>
			<div class="flex flex-col h-full" v-if="!$resources.upcomingInvoice.loading">
				<div class="flex">
					<PlanIcon />
					<div class="ml-4">
						<div class="text-4xl font-semibold ">
							{{ upcomingInvoice ? upcomingInvoice.formatted.total : '0.00' }}
						</div>
						<div class="text-base text-gray-700" v-if="upcomingInvoice">
							{{ dateShort(upcomingInvoice.period_start) }}
							→
							{{ dateShort(upcomingInvoice.period_end) }}
						</div>
						<div class="flex items-center mt-2 text-sm" v-if="paymentDate">
							<FeatherIcon
								name="calendar"
								class="inline-block w-3 h-3 text-gray-600"
							/>
							<p>
								<span class="text-gray-500 ml-1.5">
									Next Payment
								</span>
								<span class="text-gray-700">
									{{ paymentDate }}
								</span>
							</p>
						</div>
					</div>
				</div>
				<div class="p-4 mt-auto bg-gray-100 rounded" v-if="upcomingInvoice">
					<div class="flex items-center">
						<!-- prettier-ignore -->
						<svg width="26" height="20" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 6.5A1.5 1.5 0 012.5 5h17A1.5 1.5 0 0121 6.5v11a1.5 1.5 0 01-1.5 1.5h-17A1.5 1.5 0 011 17.5v-11z" stroke="url(#paint0_linear)" stroke-miterlimit="10"/><path d="M5 5V2.5A1.5 1.5 0 016.5 1h17A1.5 1.5 0 0125 2.5v9a1.5 1.5 0 01-1.5 1.5H21" stroke="url(#paint1_linear)" stroke-miterlimit="10"/><path d="M11 15a3 3 0 100-6 3 3 0 000 6z" stroke="url(#paint2_linear)" stroke-miterlimit="10"/><defs><linearGradient id="paint0_linear" x1="1" y1="5" x2="1" y2="19" gradientUnits="userSpaceOnUse"><stop stop-color="#2C9AF1"/><stop offset="1" stop-color="#2490EF"/></linearGradient><linearGradient id="paint1_linear" x1="5" y1="1" x2="5" y2="13" gradientUnits="userSpaceOnUse"><stop stop-color="#2C9AF1"/><stop offset="1" stop-color="#2490EF"/></linearGradient><linearGradient id="paint2_linear" x1="8" y1="9" x2="8" y2="15" gradientUnits="userSpaceOnUse"><stop stop-color="#2C9AF1"/><stop offset="1" stop-color="#2490EF"/></linearGradient></defs></svg>
						<div class="ml-4">
							<div class="text-base text-gray-600">Account Balance</div>
							<div class="text-lg font-medium text-gray-900">
								{{ availableCredits }}
							</div>
						</div>
						<div class="ml-auto space-x-2">
							<Button @click="showPrepaidCreditsDialog = true" type="white">
								Add Balance
							</Button>
							<Button
								v-if="$account.team.erpnext_partner"
								@click="showTransferCreditsDialog = true"
								type="white"
							>
								Transfer Credits
							</Button>
						</div>
					</div>
				</div>
			</div>
			<div
				v-if="
					!loading &&
						!$account.team.default_payment_method &&
						!$account.team.erpnext_partner
				"
			>
				<Button type="primary" route="/welcome">
					Add Billing Information
				</Button>
			</div>

			<div class="py-20 text-center" v-if="loading">
				<Button :loading="true" loadingText="Loading" />
			</div>

			<TransferCreditsDialog
				v-if="showTransferCreditsDialog"
				:show.sync="showTransferCreditsDialog"
				@success="$resources.upcomingInvoice.reload()"
			/>

			<PrepaidCreditsDialog
				v-if="showPrepaidCreditsDialog"
				:show.sync="showPrepaidCreditsDialog"
				:minimum-amount="$account.team.currency == 'INR' ? 800 : 10"
				@success="$resources.upcomingInvoice.reload()"
			/>
		</Card>
		<AccountBillingUpcomingInvoice
			:invoice-doc="upcomingInvoice"
			class="md:h-72"
		/>
	</div>
</template>
<script>
import PlanIcon from '@/components/PlanIcon.vue';
import AccountBillingUpcomingInvoice from './AccountBillingUpcomingInvoice.vue';

export default {
	name: 'AccountBillingUsage',
	components: {
		PlanIcon,
		AccountBillingUpcomingInvoice,
		TransferCreditsDialog: () => import('@/components/TransferCreditsDialog'),
		PrepaidCreditsDialog: () => import('@/components/PrepaidCreditsDialog')
	},
	resources: {
		upcomingInvoice: 'press.api.billing.upcoming_invoice'
	},
	data() {
		return {
			showTransferCreditsDialog: false,
			showPrepaidCreditsDialog: false
		};
	},
	mounted() {
		this.$socket.on('balance_updated', () =>
			this.$resources.upcomingInvoice.reload()
		);
	},
	destroyed() {
		this.$socket.off('balance_updated');
	},
	computed: {
		upcomingInvoice() {
			return this.$resources.upcomingInvoice.data?.upcoming_invoice;
		},
		availableCredits() {
			return this.$resources.upcomingInvoice.data?.available_credits;
		},
		paymentDate() {
			if (!this.upcomingInvoice) {
				return ''
			}
			let endDate = this.$date(this.upcomingInvoice.period_end);
			return endDate.toLocaleString({
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
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
