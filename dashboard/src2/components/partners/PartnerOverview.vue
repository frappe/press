<template>
	<div class="p-5 space-y-5 grid grid-cols-1 items-start gap-5 sm:grid-cols-2">
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
		<div class="mt- rounded-md border">
			<div class="flex h-12 items-center justify-between border-b px-5">
				<h2 class="text-lg font-medium text-gray-900">Partner Contribution</h2>
			</div>
			<div>
				<div
					v-for="d in contributions"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.value }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { getTeam } from '../../data/team';
export default {
	name: 'PartnerOverview',
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
		team() {
			return getTeam()?.doc;
		},
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
					value: this.team.partner_referral_code
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
	}
};
</script>
