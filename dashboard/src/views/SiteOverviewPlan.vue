<template>
	<Card
		title="Plan"
		:subtitle="
			site.status == 'Suspended'
				? 'Set a plan to activate your suspended site'
				: 'Upgrade or downgrade your plan based on your usage'
		"
		v-if="site.status != 'Inactive'"
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
				{{ site.status == 'Suspended' ? 'Set Plan' : 'Change Plan' }}
			</Button>
		</template>

		<div v-if="plan.current_plan" class="flex rounded-lg bg-gray-50 p-5">
			<PlanIcon />
			<div class="ml-4">
				<h4 class="text-4xl font-semibold text-gray-900">
					{{ $planTitle(plan.current_plan) }}
					<span v-if="plan.current_plan.price_usd > 0" class="text-lg">
						/mo
					</span>
				</h4>
				<p class="text-base text-gray-700">
					{{ plan.current_plan.cpu_time_per_day }}
					{{ $plural(plan.current_plan.cpu_time_per_day, 'hour', 'hours') }} of
					CPU / day
				</p>
			</div>
		</div>
		<div v-else class="flex rounded-lg bg-gray-50 p-5">
			<div>
				<h4 class="font-semibold text-gray-600">No Plan Set</h4>
			</div>
		</div>

		<div v-if="plan.current_plan" class="mt-4 grid grid-cols-3 gap-12">
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
		<div v-else class="mt-4 ml-2 grid grid-cols-3 gap-12">
			<div v-for="d in usage" :key="d.label">
				<div class="text-base font-medium text-gray-900">
					{{ d.label }}
				</div>
				<div class="mt-1 text-xs text-gray-600">{{ d.value }}</div>
			</div>
		</div>

		<Dialog title="Change Plan" v-model="showChangePlanDialog">
			<SitePlansTable
				class="mt-6"
				:plans="plans"
				v-model:selectedPlan="selectedPlan"
			/>
			<ErrorMessage class="mt-4" :error="$resources.changePlan.error" />
			<template #actions>
				<Button type="secondary" @click="showChangePlanDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-2"
					type="primary"
					:loading="$resources.changePlan.loading"
					@click="$resources.changePlan.submit()"
				>
					Submit
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import SitePlansTable from '@/components/SitePlansTable.vue';
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
		plans() {
			return {
				method: 'press.api.site.get_plans',
				params: {
					name: this.site?.name
				},
				default: []
			};
		},
		changePlan() {
			return {
				method: 'press.api.site.change_plan',
				params: {
					name: this.site?.name,
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
	methods: {
		plan_title(plan) {
			let india = this.$account.team.country == 'India';
			let currency = india ? '₹' : '$';
			let price_field = india ? 'price_inr' : 'price_usd';
			let price = plan.current_plan[price_field];
			return price > 0 ? `${currency}${price}` : plan.current_plan.plan_title;
		},

		belowCurrentUsage(plan) {
			return (
				this.plan.total_storage_usage > plan.max_storage_usage ||
				this.plan.total_database_usage > plan.max_database_usage
			);
		}
	},
	computed: {
		plans() {
			let processedPlans = this.$resources.plans.data.map(plan => {
				if (this.belowCurrentUsage(plan)) {
					plan.disabled = true;
				}

				if (this.site.status === 'Suspended') {
					return plan;
				}

				// If this `plan` is currently in use
				if (this.plan.current_plan.name === plan.name) {
					plan.disabled = true;
				}

				return plan;
			});

			if (this.site.status === 'Suspended') {
				processedPlans = processedPlans.filter(p => !p.disabled);
			}

			return processedPlans;
		},
		usage() {
			let f = value => {
				return this.formatBytes(value, 0, 2);
			};

			if (this.site.status === 'Suspended') {
				return [
					{
						label: 'CPU',
						value: `${this.plan.total_cpu_usage_hours} hours`
					},
					{
						label: 'Database',
						value: f(this.plan.total_database_usage)
					},
					{
						label: 'Storage',
						value: f(this.plan.total_storage_usage)
					}
				];
			}
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
					value: `${f(this.plan.total_database_usage)} / ${f(
						this.plan.current_plan.max_database_usage
					)}`,
					percentage:
						(this.plan.total_database_usage /
							this.plan.current_plan.max_database_usage) *
						100
				},
				{
					label: 'Storage',
					value: `${f(this.plan.total_storage_usage)} / ${f(
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
