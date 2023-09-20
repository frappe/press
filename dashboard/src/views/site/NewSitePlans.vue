<template>
	<div>
		<label class="text-lg font-semibold"> Choose your plan </label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your site.
		</p>
		<div class="mt-4">
			<div v-if="$resources.plans.loading" class="flex justify-center">
				<LoadingText />
			</div>
			<SitePlansTable
				v-if="plans"
				:plans="plans"
				:selectedPlan="selectedPlan"
				@update:selectedPlan="plan => $emit('update:selectedPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import SitePlansTable from '@/components/SitePlansTable.vue';

export default {
	name: 'Plans',
	emits: ['update:selectedPlan'],
	props: ['bench', 'selectedPlan', 'benchTeam'],
	components: {
		SitePlansTable
	},
	data() {
		return {
			plans: null
		};
	},
	resources: {
		plans() {
			return {
				url: 'press.api.site.get_plans',
				params: {
					rg: this.bench
				},
				auto: true,
				onSuccess(r) {
					this.plans = r.map(plan => {
						plan.disabled = !this.$account.hasBillingInfo;
						return plan;
					});
				}
			};
		}
	}
};
</script>
