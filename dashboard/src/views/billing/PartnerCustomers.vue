<template>
	<Card
		title="Partner Customers"
		subtitle="Customers associated with your account"
		v-if="$account.team.erpnext_partner"
	>
		<div class="max-h-96 divide-y">
			<div
				class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-600"
			>
				<span>Email</span>
				<span>Team</span>
				<span>Payment Mode</span>
			</div>
			<div
				:key="customer.team"
				v-for="customer in partnerCustomers"
				class="grid grid-cols-3 items-center gap-x-8 py-4 text-base text-gray-900"
			>
				<span>{{ customer.email }}</span>
				<span>{{ customer.team }}</span>
				<span>
					{{ customer.payment_mode }}
				</span>
			</div>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'PartnerCustomers',
	data() {
		return {
			partnerCustomers: []
		};
	},
	resources: {
		getPartnerCustomers: {
			url: 'press.api.account.get_partner_customers',
			onSuccess(data) {
				this.partnerCustomers = data.map(d => {
					return {
						email: d.user,
						team: d.name,
						payment_mode: d.payment_mode
					};
				});
			},
			auto: true
		}
	}
};
</script>
