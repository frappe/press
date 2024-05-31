<template>
	<div class="p-5">
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
				<div class="h-12 border-b px-5 py-4">
					<h2
						class="text-lg font-medium text-gray-900 flex items-center justify-between"
					>
						Partner Contribution
						<Button @click="showPartnerContributionDialog = true"
							>Details</Button
						>
					</h2>
				</div>
				<div>
					<div
						v-for="d in contributions"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
						<div
							v-if="d.label != 'Certification'"
							class="w-2/3 text-base font-medium"
						>
							{{ formatCurrency(d.value) }}
						</div>
						<div v-else class="w-2/3 text-base font-medium">
							{{ d.value }}
						</div>
					</div>
				</div>
			</div>
		</div>
		<Dialog
			:show="showPartnerContributionDialog"
			v-model="showPartnerContributionDialog"
			:options="{ size: '3xl', title: 'Contributions of this month' }"
		>
			<template #body-content>
				<PartnerContribution :partnerEmail="$team.doc.partner_email" />
			</template>
		</Dialog>
	</div>
</template>

<script>
import PartnerContribution from './PartnerContribution.vue';
export default {
	name: 'PartnerOverview',
	data() {
		return {
			showPartnerContributionDialog: false
		};
	},
	components: {
		PartnerContribution
	},
	resources: {
		partner() {
			return {
				url: 'press.api.partner.get_partner_details',
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
					label: 'Certification',
					value:
						this.$resources.partner.data?.custom_number_of_certified_members
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
		}
	}
};
</script>
