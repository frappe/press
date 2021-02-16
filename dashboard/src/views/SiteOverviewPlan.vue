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
			<div
				class="flex items-center justify-center w-12 h-12 bg-white rounded-full shadow"
			>
				<svg
					width="21"
					height="25"
					viewBox="0 0 21 25"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						class="text-blue-500"
						d="M0 8.9V15.5C0 16.6324 1.20672 17.3564 2.20588 16.8235L14.2059 10.4235C14.6947 10.1628 15 9.65397 15 9.1V2.5C15 1.36762 13.7933 0.643586 12.7941 1.17647L0.794118 7.57647C0.305322 7.83716 0 8.34603 0 8.9Z"
						fill="currentColor"
					/>
					<path
						class="text-blue-400"
						opacity="0.3"
						d="M6 15.7V22.3C6 23.4324 7.20672 24.1564 8.20588 23.6235L20.2059 17.2235C20.6947 16.9628 21 16.454 21 15.9V9.29999C21 8.16761 19.7933 7.44357 18.7941 7.97646L6.79412 14.3765C6.30532 14.6371 6 15.146 6 15.7Z"
						fill="currentColor"
					/>
				</svg>
			</div>
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
					{{ d.label }} {{ isNaN(d.percentage) ? '' : `(${Number(d.percentage).toFixed(1)}%)` }}
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
export default {
	name: 'SiteOverviewPlan',
	props: ['site', 'plan'],
	components: {
		SitePlansTable,
		ProgressArc
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
