<template>
	<Card
		title="Partner Customers"
		subtitle="Customers associated with your account"
		v-if="$account.team.erpnext_partner"
	>
		<div class="max-h-96 divide-y">
			<div
				class="grid grid-cols-4 items-center gap-x-8 py-4 text-base text-gray-600"
			>
				<span>Name</span>
				<span>Email</span>
				<span>Currency</span>
				<span>Payment Mode</span>
			</div>
			<div
				:key="customer.team"
				v-for="customer in partnerCustomers"
				class="grid grid-cols-4 items-center gap-x-8 py-4 text-base text-gray-900"
			>
				<span>{{ customer.billing_name }}</span>
				<span>{{ customer.email }}</span>
				<span>{{ customer.currency }}</span>
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
						billing_name: d.billing_name || '',
						payment_mode: d.payment_mode || '',
						currency: d.currency
					};
				});
			},
			auto: true
		}
	}
};
</script>
