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
		'serverPlanPrice',
		'serverSupportQuotaAvailable',
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
		providerForPlans() {
			return ['Generic', 'Scaleway'].includes(this.selectedProvider)
				? 'AWS EC2'
				: this.selectedProvider;
		},
		currentPlan: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		plans() {
			let plans = getPlans().filter(
				(plan) => !!plan.dedicated_server_plan === !!this.isDedicatedServerSite,
			);

			if (this.hideRestrictedPlans) {
				plans = plans.filter((plan) => !plan.restricted_plan);
			}
			// Hide plans of other providers: each has its own price list
			if (this.selectedProvider) {
				plans = plans.filter((plan) =>
					this.allows(plan.cloud_providers, this.providerForPlans),
				);
			}

			return plans.map((plan) => {
				// Show a plan that does not fit as disabled with the reason, not hide it
				const disabledReason = this.getDisabledReason(plan);
				return {
					...plan,
					disabled: !!disabledReason,
					disabledReason,
					sublabel: plan.plan_description || null,
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
							value: plan.private_benches ? 'Private Bench & Custom Apps' : '',
						},
						{
							value: plan.monitor_access ? 'Advanced Monitoring' : '',
						},
					].filter((feature) => feature.condition ?? true),
				};
			});
		},
	},
	watch: {
		plans: {
			immediate: true,
			handler: function (plans) {
				if (!this.isDedicatedServerSite) return;

				if (!plans.length) return;

				const bestPlan = this.getBestDedicatedSitePlan();

				if (bestPlan) {
					this.currentPlan = bestPlan;
				}
			},
		},
	},
	methods: {
		getDisabledReason(plan) {
			if (this.isPrivateBenchSite && !plan.private_benches) {
				return 'Not available on a private bench';
			}
			if (
				this.isDedicatedServerSite &&
				plan.restrict_based_on_dedicated_server_plan &&
				// An unknown server price does not meet the minimum
				!(this.serverPlanPrice >= plan.minimum_server_price_usd)
			) {
				return `Needs a server plan of $${plan.minimum_server_price_usd}/mo or more`;
			}
			if (
				this.selectedCluster &&
				!this.allows(plan.clusters, this.selectedCluster)
			) {
				return 'Not available in this region';
			}
			if (
				this.selectedApps &&
				!this.selectedApps.every((app) =>
					this.allows(plan.allowed_apps, app.app),
				)
			) {
				return 'Not available for the selected apps';
			}
			if (
				this.selectedVersion &&
				!this.allows(plan.bench_versions, this.selectedVersion)
			) {
				return 'Not available for this version';
			}
			return null;
		},
		// An empty list means that the plan has no restriction
		allows(allowedValues, value) {
			return !allowedValues?.length || allowedValues.includes(value);
		},
		// Currently best plan is determined based on warranty and CPU time only (may change later)
		getBestDedicatedSitePlan() {
			let filteredPlans = this.plans.filter((plan) => !plan.disabled);

			if (this.serverSupportQuotaAvailable) {
				filteredPlans = filteredPlans.filter((plan) => plan.support_included);
			}
			if (!filteredPlans.length) return null;

			const bestPlan = filteredPlans.reduce((best, curr) => {
				return parseFloat(curr.cpu_time_per_day) >
					parseFloat(best.cpu_time_per_day)
					? curr
					: best;
			});

			return bestPlan;
		},
	},
};
</script>
