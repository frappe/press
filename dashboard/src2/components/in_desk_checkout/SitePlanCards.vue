<template>
	<div class="@container">
		<div class="grid grid-cols-2 gap-3 @xl:grid-cols-3">
			<PlanCard
				v-for="plan in plans"
				:plan="plan"
				:selected="currentPlan.name === plan.name"
				@select="() => setPlan(plan)"
			/>
		</div>
	</div>
</template>

<script>
import PlanCard from './PlanCard.vue';

export default {
	name: 'SitePlanCards',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: {
		PlanCard
	},
	inject: ['team'],
	resources: {
		saas_plans() {
			return {
				url: 'press.saas.api.site.get_plans',
				auto: true,
				initialData: []
			};
		}
	},
	methods: {
		setPlan(plan) {
			this.$emit('update:modelValue', plan);
		}
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
		teamCurrency: {
			get() {
				return this.team.data?.currency || 'USD';
			}
		},
		plans() {
			let plans = this.$resources.saas_plans?.data ?? [];
			plans = plans.filter(plan => !plan.dedicated_server_plan);

			return plans.map(plan => {
				return {
					...plan,
					label: plan.plan_title,
					sublabel:
						this.teamCurrency == 'USD'
							? `$${plan.price_usd} / month`
							: `₹${plan.price_inr} / month`,
					features: [
						{
							label: `${this.$format.plural(
								plan.cpu_time_per_day,
								'compute hour',
								'compute hours'
							)} / day`,
							condition: !plan.name.includes('Unlimited'),
							value: plan.cpu_time_per_day
						},
						{
							label: 'Database',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_database_usage, 0, 2)
						},
						{
							label: 'Disk',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_storage_usage, 1, 2)
						},
						{
							value: 'Product Warranty'
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
					].filter(feature => feature.condition ?? true)
				};
			});
		}
	}
};
</script>
