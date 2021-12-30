<template>
	<div>
		<ErrorMessage :error="$resources.getAppPlans.error" />

		<Button
			v-if="$resources.getAppPlans.loading"
			:loading="true"
			loadingText="Loading Plans..."
		></Button>

		<div v-if="plans" class="mx-auto flex flex-row gap-x-6">
			<AppPlanCard
				v-for="plan in plans"
				:plan="plan"
				:key="plan.name"
				:popular="Boolean(plan.marked_most_popular)"
				:selected="selectedPlan == plan"
				@click.native="handleCardClick(plan)"
			/>
		</div>
	</div>
</template>

<script>
import AppPlanCard from '@/components/AppPlanCard.vue';

export default {
	name: 'ChangeAppPlanCards',
	components: {
		AppPlanCard
	},
	props: ['currentPlan'],
	model: {
		prop: 'selectedPlan',
		event: 'change'
	},
	data() {
		return {
			selectedPlan: null
		};
	},
	mounted() {
		if (this.currentPlan) {
			// TODO: Handle already selected plan
		}
	},
	resources: {
		getAppPlans() {
			return {
				method: 'press.api.marketplace.get_app_plans',
				params: {
					app: 'darkify' // TODO: Replace with prop 'app'
				},
				auto: true
			};
		}
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
			this.$emit('change', plan);
		}
	},
	computed: {
		plans() {
			if (
				this.$resources.getAppPlans.data &&
				!this.$resources.getAppPlans.loading
			) {
				return this.$resources.getAppPlans.data;
			}
		}
	}
};
</script>
