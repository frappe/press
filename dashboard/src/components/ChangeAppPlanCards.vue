<template>
	<div class="mx-auto flex flex-row gap-x-6">
		<AppPlanCard
			v-for="plan in plans"
			:plan="plan"
			:key="plan.price"
			:popular="plan.isMostPopular"
			:selected="selectedPlan == plan"
			@click.native="handleCardClick(plan)"
		/>
	</div>
</template>

<script>
import AppPlanCard from '@/components/AppPlanCard.vue';

export default {
	name: 'ChangeAppPlanCards',
	components: {
		AppPlanCard
	},
	data() {
		return {
			selectedPlan: null,
			plans: [
				{
					price: '₹99',
					discountedFrom: '₹299',
					features: ['1 member', '7 day data retention', '1 GB']
				},
				{
					price: '₹149',
					discountedFrom: '₹499',
					features: ['12 member', '14 day data retention', '5 GB'],
					isMostPopular: true
				},
				{
					price: '₹390',
					discountedFrom: '₹799',
					features: ['40 member', '1 year data retention', 'Unlimited']
				}
			]
		};
	},
	resources: {
		getAppPlans() {
			return {
				method: 'press.api.marketplace.get_app_plans',
				params: {
					app: 'darkify' // TODO: Replace with prop 'app'
				},
				auto: true,
				onSuccess(d) {
					console.log(d);
				}
			};
		}
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
		}
	}
};
</script>
