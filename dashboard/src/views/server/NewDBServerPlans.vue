<template>
	<div>
		<label class="text-lg font-semibold">
			Choose your database server plan
		</label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your
			database server.
		</p>
		<AlertBillingInformation class="mt-4" />
		<div class="mt-4">
			<ServerPlansTable
				:plans="dbPlanOptions"
				:selectedPlan="selectedDBPlan"
				@update:selectedPlan="(plan) => $emit('update:selectedDBPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import ServerPlansTable from '@/components/ServerPlansTable.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'DBServerPlans',
	emits: ['update:selectedDBPlan'],
	props: ['options', 'selectedDBPlan', 'selectedRegion'],
	components: {
		ServerPlansTable,
		AlertBillingInformation,
	},
	computed: {
		dbPlanOptions() {
			if (
				this.selectedRegion === 'Mumbai' ||
				this.selectedRegion === 'Frankfurt'
			) {
				return this.options.db_plans.filter(
					(plan) =>
						plan.cluster == this.selectedRegion && plan.platform == 'arm64',
				);
			}
			return this.options.db_plans.filter(
				(plan) => plan.cluster == this.selectedRegion,
			);
		},
	},
};
</script>
