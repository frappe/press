<template>
	<Card
		title="Plan"
		:subtitle="'Upgrade or downgrade your plan based on your usage'"
	>
	</Card>
</template>
<script>
export default {
	name: 'ServerOverviewPlan',
	props: ['server', 'plan'],
	components: {
	},
	data() {
		return {
		};
	},
	resources: {
	},
	methods: {
		plan_title(plan) {
			let india = this.$account.team.country == 'India';
			let currency = india ? '₹' : '$';
			let price_field = india ? 'price_inr' : 'price_usd';
			let price = plan[price_field];
			return price > 0 ? `${currency}${price}` : plan.plan_title;
		},

	},
};
</script>
