<template>
	<div>
		<label class="text-lg font-semibold">
			Choose your plan
		</label>
		<p class="text-base text-gray-700">
			Select a plan based on the type of usage you are expecting on your site.
		</p>
		<AlertBillingInformation class="mt-4" />
		<div class="mt-4">
			<SitePlansTable
				:plans="options.plans"
				:selectedPlan="selectedPlan"
				@change="plan => $emit('update:selectedPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import SitePlansTable from '@/components/SitePlansTable.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'Plans',
	props: ['options', 'selectedPlan'],
	components: {
		SitePlansTable,
		AlertBillingInformation
	}
};
</script>
