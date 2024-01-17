<template>
	<div class="p-5">
		<div class="grid grid-cols-2 gap-5">
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">Partner Overview</h2>
				</div>
				<div>
					<div
						v-for="d in partnerOverview"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/2 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-1/2 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
			<div class="rounded-md border">
				<div class="h-12 border-b px-5 py-4">
					<h2 class="text-lg font-medium text-gray-900">
						Target Contributions
					</h2>
				</div>
				<div>
					<div
						v-for="d in contributions"
						:key="d.label"
						class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
					>
						<div class="w-1/2 text-base text-gray-700">{{ d.label }}</div>
						<div class="w-1/2 text-base font-medium">{{ d.value }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'PartnerOverview',
	computed: {
		partnerOverview() {
			return [
				{
					label: 'Referral Code',
					value: 'edc4fe33'
				},
				{
					label: 'Tier Level',
					value: 'Gold'
				},
				{
					label: 'Active Certifcations',
					value: 4
				},
				{
					label: 'Linked Customers',
					value: 6
				},
				{
					label: 'Partner Members',
					value: 3
				},
				{
					label: 'Partner Email',
					value: this.$team.doc.partner_email
				}
			];
		},
		contributions() {
			return [
				{
					label: 'Total Contributions',
					value: 34785
				},
				{
					label: 'Frappe Cloud',
					value: 12045
				},
				{
					label: 'Enterprise',
					value: 22740
				}
			];
		}
	}
};
</script>
