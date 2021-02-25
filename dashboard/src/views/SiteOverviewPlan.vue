<template>
	<Card
		title="Plan"
		subtitle="Upgrade or downgrade your plan based on your usage"
	>
		<template #actions>
			<Button
				v-if="['Active', 'Suspended'].includes(site.status)"
				@click="
					() => {
						showChangePlanDialog = true;
						!plans.length && $resources.plans.fetch();
					}
				"
			>
				Change Plan
			</Button>
		</template>
		<div class="flex p-5 rounded-lg bg-gray-50">
			<PlanIcon />
			<div class="ml-4">
				<h4 class="text-4xl font-semibold text-gray-900">
					${{ plan.current_plan.price_usd }}
					<span class="text-lg">/mo</span>
				</h4>
				<p class="text-base text-gray-700">
					{{ plan.current_plan.cpu_time_per_day }}
					{{ $plural(plan.current_plan.cpu_time_per_day, 'hour', 'hours') }} of
					CPU / day
				</p>
			</div>
		</div>
		<div class="grid grid-cols-3 gap-12 mt-4">
			<div v-for="d in usage" :key="d.label">
				<ProgressArc :percentage="d.percentage" />
				<div class="mt-2 text-base font-medium text-gray-900">
					{{ d.label }}
					{{
						isNaN(d.percentage) ? '' : `(${Number(d.percentage).toFixed(1)}%)`
					}}
				</div>
				<div class="mt-1 text-xs text-gray-600">{{ d.value }}</div>
			</div>
		</div>

		<Dialog title="Change Plan" v-model="showChangePlanDialog">
			<SitePlansTable class="mt-6" :plans="plans" v-model="selectedPlan" />
			<ErrorMessage class="mt-4" :error="$resources.changePlan.error" />
			<template #actions>
				<Button type="secondary" @click="showChangePlanDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-2"
					type="primary"
					@click="$resources.changePlan.submit()"
				>
					Submit
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import SitePlansTable from '@/components/SitePlansTable';
import ProgressArc from '@/components/ProgressArc.vue';
import PlanIcon from '@/components/PlanIcon.vue';

export default {
	name: 'SiteOverviewPlan',
	props: ['site', 'plan'],
	components: {
		SitePlansTable,
		ProgressArc,
		PlanIcon
	},
	data() {
		return {
			showChangePlanDialog: false,
			selectedPlan: null
		};
	},
	resources: {
		plans: {
			method: 'press.api.site.get_plans',
			default: []
		},
		changePlan() {
			return {
				method: 'press.api.site.change_plan',
				params: {
					name: this.site.name,
					plan: this.selectedPlan?.name
				},
				onSuccess() {
					this.$notify({
						title: `Plan changed to ${this.selectedPlan.plan_title}`,
						icon: 'check',
						color: 'green'
					});
					this.showChangePlanDialog = false;
					this.selectedPlan = null;
					this.$emit('plan-change');
					this.$resources.plans.reset();
				}
			};
		}
	},
	computed: {
		plans() {
			return this.$resources.plans.data.map(plan => {
				if (this.plan.current_plan.name === plan.name) {
					plan.disabled = true;
				}

				if (
					this.plan.total_storage_usage > plan.max_storage_usage ||
					this.plan.total_database_usage > plan.max_database_usage
				) {
					plan.disabled = true;
				}
				return plan;
			});
		},
		usage() {
			let f = value => {
				return this.formatBytes(value, 0, 2);
			};
			return [
				{
					label: 'CPU',
					value: `${this.plan.total_cpu_usage_hours} / ${
						this.plan.current_plan.cpu_time_per_day
					} ${this.$plural(
						this.plan.current_plan.cpu_time_per_day,
						'hour',
						'hours'
					)}`,
					percentage:
						(this.plan.total_cpu_usage_hours /
							this.plan.current_plan.cpu_time_per_day) *
						100
				},
				{
					label: 'Database',
					value: `${this.plan.total_database_usage} / ${f(
						this.plan.current_plan.max_database_usage
					)}`,
					percentage:
						(this.plan.total_database_usage /
							this.plan.current_plan.max_database_usage) *
						100
				},
				{
					label: 'Storage',
					value: `${this.plan.total_storage_usage} / ${f(
						this.plan.current_plan.max_storage_usage
					)}`,
					percentage:
						(this.plan.total_storage_usage /
							this.plan.current_plan.max_storage_usage) *
						100
				}
			];
		}
	}
};
</script>
