<template>
	<PlansCards v-model="currentPlan" :plans="plans" />
</template>

<script>
import PlansCards from './PlansCards.vue';
import { getPlans } from '../data/plans';

export default {
	name: 'SitePlansCards',
	props: ['modelValue', 'isPrivateBenchSite', 'isDedicatedServerSite'],
	emits: ['update:modelValue'],
	components: {
		PlansCards
	},
	computed: {
		currentPlan: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		},
		plans() {
			let plans = getPlans();
			if (this.isPrivateBenchSite)
				plans = plans.filter(plan => plan.private_benches);
			if (this.isDedicatedServerSite)
				plans = plans.filter(plan => plan.dedicated_server_plan);
			else plans = plans.filter(plan => !plan.dedicated_server_plan);

			return plans.map(plan => {
				return {
					...plan,
					features: [
						{
							label: `${this.$format.plural(
								plan.cpu_time_per_day,
								'compute hour',
								'compute hours'
							)} / day`,
							value: plan.cpu_time_per_day
						},
						{
							label: 'Database',
							value: this.$format.bytes(plan.max_database_usage, 0, 2)
						},
						{
							label: 'Disk',
							value: this.$format.bytes(plan.max_storage_usage, 0, 2)
						},
						{
							value: plan.support_included ? 'Support Included' : ''
						},
						{
							value: plan.database_access ? 'Database Access' : ''
						},
						{
							value: plan.offsite_backups ? 'Offsite Backups' : ''
						},
						{
							value: plan.monitor_access ? 'Advanced Monitoring' : ''
						}
					]
				};
			});
		}
	}
};
</script>
