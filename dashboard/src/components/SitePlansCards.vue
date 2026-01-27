<template>
	<PlansCards v-model="currentPlan" :plans="plans" />
</template>

<script>
import PlansCards from './PlansCards.vue';
import { getPlans } from '../data/plans';

export default {
	name: 'SitePlansCards',
	props: [
		'modelValue',
		'isPrivateBenchSite',
		'isDedicatedServerSite',
		'selectedCluster',
		'selectedApps',
		'selectedVersion',
		'selectedProvider',
		'hideRestrictedPlans',
	],
	emits: ['update:modelValue'],
	components: {
		PlansCards,
	},
	computed: {
		currentPlan: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		plans() {
			let plans = getPlans();

			if (this.isPrivateBenchSite) {
				plans = plans.filter((plan) => plan.private_benches);
			}
			if (this.isPrivateBenchSite && this.isDedicatedServerSite) {
				plans = plans.filter((plan) => plan.dedicated_server_plan);
			} else {
				plans = plans.filter((plan) => !plan.dedicated_server_plan);
			}
			if (this.selectedCluster) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.clusters.length == 0
								? false
								: !plan.clusters.includes(this.selectedCluster)),
					};
				});
			}
			if (this.selectedApps) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.allowed_apps.length == 0
								? false
								: !this.selectedApps.every((app) =>
										plan.allowed_apps.includes(app.app),
									)),
					};
				});
			}
			if (this.selectedVersion) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.bench_versions.length == 0
								? false
								: !plan.bench_versions.includes(this.selectedVersion)),
					};
				});
			}
			if (this.hideRestrictedPlans) {
				plans = plans.filter((plan) => !plan.restricted_plan);
			}
			if (this.selectedProvider) {
				const provider = ["Generic", "Scaleway"].includes(
					this.selectedProvider,
				)
					? "AWS EC2"
					: this.selectedProvider;

				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.cloud_providers && plan.cloud_providers.length > 0
								? !plan.cloud_providers.includes(provider)
								: false),
					};
				});
			}

			plans = plans.filter((plan) => !plan.disabled);

			return plans.map((plan) => {
				return {
					...plan,
					features: [
						{
							label: `${this.$format.plural(
								plan.cpu_time_per_day,
								'compute hour',
								'compute hours',
							)} / day`,
							condition: !plan.name.includes('Unlimited'),
							value: plan.cpu_time_per_day,
						},
						{
							label: 'Database',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_database_usage, 1, 2),
						},
						{
							label: 'Disk',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_storage_usage, 1, 2),
						},
						{
							value: plan.name.includes('Unlimited - Low')
								? 'Allocate fewer resources here (more for other benches)'
								: '',
						},
						{
							value: plan.support_included ? 'Product Warranty' : '',
						},
						{
							value: plan.database_access ? 'Database Access' : '',
						},
						{
							value: plan.offsite_backups ? 'Offsite Backups' : '',
						},
						{
							value: plan.monitor_access ? 'Advanced Monitoring' : '',
						},
					].filter((feature) => feature.condition ?? true),
				};
			});
		},
	},
};
</script>
