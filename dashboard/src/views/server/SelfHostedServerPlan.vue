<template>
	<div>
		<label class="text-lg font-semibold">
			We have a fixed Pricing for managing Self Hosted Servers
		</label>
		<AlertBillingInformation class="mt-4" />
		<div class="mt-4">
			<ServerPlansTable
				:plans="planOptions"
				:selectedPlan="selectedPlan"
				@update:selectedPlan="plan => $emit('update:selectedPlan', plan)"
			/>
		</div>
	</div>
</template>
<script>
import ServerPlansTable from '@/components/ServerPlansTable.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'SelfHostedServerPlan',
	emits: ['update:selectedPlan'],
	props: ['options', 'selectedPlan'],
	components: {
		ServerPlansTable,
		AlertBillingInformation
	},
    computed: {
		planOptions() {
			return this.options
		}
	}
};
</script>
