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
				v-if="['Active', 'Suspended'].includes(site.status) && canChangePlan"
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
				<p
					class="text-base text-gray-700"
					v-if="plan.current_plan.name != 'Unlimited'"
				>
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
			<div
				v-if="plan.current_plan.name != 'Unlimited'"
				v-for="d in usage"
				:key="d.label"
			>
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
		<div v-else class="ml-2 mt-4 grid grid-cols-3 gap-12">
			<div v-for="d in usage" :key="d.label">
				<div class="text-base font-medium text-gray-900">
					{{ d.label }}
				</div>
				<div class="mt-1 text-xs text-gray-600">{{ d.value }}</div>
			</div>
		</div>

		<SitePlansDialog
			:site="site"
			:plan="plan"
			v-model="showChangePlanDialog"
			@plan-change="() => $emit('plan-change')"
		/>
	</Card>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import SitePlansTable from '@/components/SitePlansTable.vue';
import ProgressArc from '@/components/ProgressArc.vue';
import PlanIcon from '@/components/PlanIcon.vue';

export default {
	name: 'SiteOverviewPlan',
	props: ['site', 'plan'],
	components: {
		SitePlansTable,
		ProgressArc,
		SitePlansDialog: defineAsyncComponent(() =>
			import('./SitePlansDialog.vue')
		),
		PlanIcon
	},
	data() {
		return {
			showChangePlanDialog: false,
			selectedPlan: null,
			validationMessage: null
		};
	},
	watch: {
		async selectedPlan(value) {
			try {
				// custom plan validation for frappe support
				let result = await this.$call('validate_plan_change', {
					current_plan: this.plan.current_plan,
					new_plan: value,
					currency: this.$account.team.currency
				});
				this.validationMessage = result;
			} catch (e) {
				this.validationMessage = null;
			}
		}
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
		getCurrentFormattedUsage() {
			let f = value => {
				return this.formatBytes(value, 0, 2);
			};

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
	},
	computed: {
		canChangePlan() {
			return this.site.can_change_plan;
		},
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

			if (!this.plan.current_plan || this.site.status === 'Suspended') {
				return this.getCurrentFormattedUsage();
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
