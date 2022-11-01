<template>
	<div>
		<label class="text-lg font-semibold">
			Choose your application server plan
		</label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your
			application server.
		</p>
		<AlertBillingInformation class="mt-4" />
		<div class="mt-4">
			<ServerPlansTable
				:plans="appPlanOptions"
				:selectedPlan="selectedAppPlan"
				@update:selectedPlan="plan => $emit('update:selectedAppPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import ServerPlansTable from '@/components/ServerPlansTable.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'AppServerPlans',
	emits: ['update:selectedAppPlan'],
	props: ['options', 'selectedAppPlan', 'selectedRegion'],
	components: {
		ServerPlansTable,
		AlertBillingInformation
	},
	computed: {
		appPlanOptions() {
			return this.options.app_plans.filter(
				plan => plan.cluster == this.selectedRegion
			);
		}
	}
};
</script>
