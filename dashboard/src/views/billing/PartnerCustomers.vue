<template>
	<Card
		title="Partner Customers"
		subtitle="Customers associated with your account"
		v-if="$account.team.erpnext_partner"
	>
		<ListItem
			v-for="customer in partnerCustomers"
			:title="customer.email"
			:description="customer.team"
			:key="customer.team"
		>
		</ListItem>
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
			method: 'press.api.account.get_partner_customers',
			onSuccess(data) {
				this.partnerCustomers = data.map(d => {
					return {
						email: d.user,
						team: d.name
					};
				});
			},
			auto: true
		}
	}
};
</script>
