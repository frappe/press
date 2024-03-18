<template>
	<div class="p-5">
		<div class="px-3 rounded-md border py-5 mb-2">
			<Progress
				size="lg"
				:value="calculateNextTier().partnerProgress"
				label="Partner Contribution"
			>
				<template #hint>
					<span class="text-base font-medium text-gray-500">
						{{ calculateNextTier().nextTierTarget }}
					</span>
				</template>
			</Progress>

			<div>
				<div class="mt-2 flex justify-between">
					<div class="text-sm text-gray-600">
						Current Contribution:
						{{
							formatCurrency(
								$resources.partner.data
									?.custom_ongoing_period_revenue_contribution
							)
						}}
					</div>
					<div class="text-sm text-gray-600">
						Next Tier: {{ calculateNextTier().nextTier }}
					</div>
				</div>
			</div>
		</div>
		<div class="pt-3 grid grid-cols-1 items-start gap-5 sm:grid-cols-2">
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">Partner Details</h2>
				</div>
				<div>
					<div
						v-for="d in partnerDetails"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4 flex items-center justify-between">
					<h2 class="text-lg font-medium text-gray-900">
						Partner Contribution
					</h2>
					<Button @click="showPartnerContributionDialog = true">
						Details
					</Button>
				</div>
				<div>
					<div
						v-for="d in contributions"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-2/3 text-base font-medium">
							{{ formatCurrency(d.value) }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<Dialog
			:show="showPartnerContributionDialog"
			v-model="showPartnerContributionDialog"
			:options="{ title: 'Contributions of this month', size: '3xl' }"
		>
			<template #body-content>
				<PartnerContributionTable :partnerEmail="$team.doc.partner_email" />
			</template>
		</Dialog>
	</div>
</template>

<script>
import { Progress } from 'frappe-ui';
import PartnerContributionTable from './PartnerContributionTable.vue';

export default {
	name: 'PartnerOverview',
	data() {
		return {
			showPartnerContributionDialog: false,
			partnerProgress: 0
		};
	},
	resources: {
		partner() {
			return {
				url: 'press.api.account.get_partner_details',
				auto: true,
				params: {
					partner_email: this.$team.doc.partner_email
				}
			};
		}
	},
	computed: {
		partnerDetails() {
			return [
				{
					label: 'Name',
					value: this.$resources.partner.data?.partner_name
				},
				{
					label: 'Email',
					value: this.$resources.partner.data?.email
				},
				{
					label: 'Company Name',
					value: this.$resources.partner.data?.company_name
				},
				{
					label: 'Current Tier',
					value: this.$resources.partner.data?.partner_type
				},
				{
					label: 'Code',
					value: this.$team.doc.partner_referral_code
				}
			];
		},
		contributions() {
			return [
				{
					label: 'Frappe Cloud',
					value:
						this.$resources.partner.data
							?.custom_ongoing_period_fc_invoice_contribution
				},
				{
					label: 'Enterprise',
					value:
						this.$resources.partner.data
							?.custom_ongoing_period_enterprise_invoice_contribution
				},
				{
					label: 'Total',
					value:
						this.$resources.partner.data
							?.custom_ongoing_period_revenue_contribution
				}
			];
		}
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			let currency = this.$team.doc.currency;
			return this.$format.currency(value, currency);
		},
		calculateNextTier() {
			let partnerCurrency = this.$team.doc.currency;
			var partnerUsdTarget = {
				Bronze: 3200,
				Silver: 16000,
				Gold: 32000
			};
			var partnerInrTarget = {
				Bronze: 250000,
				Silver: 1250000,
				Gold: 2500000
			};
			let currentContribution =
				this.$resources.partner.data
					?.custom_ongoing_period_revenue_contribution;
			let currentTier = this.$resources.partner.data?.partner_type;

			if (currentTier == 'Gold') {
				let nextTierTarget = 0.0;
				if (partnerCurrency == 'INR') {
					nextTierTarget = partnerInrTarget['Gold'];
				} else {
					nextTierTarget = partnerUsdTarget['Gold'];
				}
				return {
					nextTier: 'Gold',
					partnerProgress: 100,
					nextTierTarget: this.formatCurrency(nextTierTarget)
				};
			} else {
				let nextTier = '';
				let partnerProgress = 0;
				let nextTierTarget = 0.0;
				if (currentTier == 'Bronze') {
					nextTier = 'Silver';
					if (partnerCurrency == 'INR') {
						partnerProgress =
							(currentContribution / partnerInrTarget[nextTier]) * 100;
						nextTierTarget = partnerInrTarget[nextTier];
					} else {
						partnerProgress =
							(currentContribution / partnerUsdTarget[nextTier]) * 100;
						nextTierTarget = partnerUsdTarget[nextTier];
					}
				} else if (currentTier == 'Silver') {
					nextTier = 'Gold';
					if (partnerCurrency == 'INR') {
						partnerProgress =
							(currentContribution / partnerInrTarget[nextTier]) * 100;
						nextTierTarget = partnerInrTarget[nextTier];
					} else {
						partnerProgress =
							(currentContribution / partnerUsdTarget[nextTier]) * 100;
						nextTierTarget = partnerUsdTarget[nextTier];
					}
				}
				return {
					nextTier: nextTier,
					partnerProgress: partnerProgress,
					nextTierTarget: this.formatCurrency(nextTierTarget)
				};
			}
		}
	},
	components: { Progress, PartnerContributionTable }
};
</script>
