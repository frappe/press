<template>
	<Card
		title="Plan"
		:subtitle="'Upgrade or downgrade your plan based on your usage'"
	>
		<template #actions>
			<Button
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

		<div v-if="plan" class="flex rounded-lg bg-gray-50 p-5">
			<PlanIcon />
			<div class="ml-4">
				<h4 class="text-4xl font-semibold text-gray-900">
					{{ $planTitle(plan) }}
					<span v-if="plan.price_usd > 0" class="text-lg"> /mo </span>
				</h4>
				<p class="text-base text-gray-700">
					{{ plan.vcpu }} {{ $plural(plan.vcpu, 'vCPU', 'vCPUs') }} +
					{{ formatBytes(plan.memory, 0, 2) }} Memory +
					{{ formatBytes(plan.disk, 0, 3) }} Storage
				</p>
			</div>
		</div>
		<div v-if="plan && used?.memory" class="mt-4 grid grid-cols-3 gap-12">
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

		<Dialog
			:options="{
				title: 'Change Plan',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						loading: $resources.changePlan.loading,
						onClick: () => $resources.changePlan.submit()
					}
				]
			}"
			v-model="showChangePlanDialog"
		>
			<template v-slot:body-content>
				<ServerPlansTable
					class="mt-6"
					:plans="plans"
					v-model:selectedPlan="selectedPlan"
				/>
				<ErrorMessage class="mt-4" :message="$resources.changePlan.error" />
			</template>
		</Dialog>
	</Card>
</template>
<script>
import ServerPlansTable from '@/components/ServerPlansTable.vue';
import ProgressArc from '@/components/ProgressArc.vue';
import PlanIcon from '@/components/PlanIcon.vue';

export default {
	name: 'ServerOverviewPlan',
	props: ['server', 'plan'],
	components: {
		ServerPlansTable,
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
		usageResource() {
			return {
				method: 'press.api.server.usage',
				params: {
					name: this.server?.name
				},
				default: {},
				auto: true
			};
		},
		plans() {
			return {
				method: 'press.api.server.plans',
				params: {
					name: 'Server',
					cluster: this.server.region_info.name
				},
				default: []
			};
		},
		changePlan() {
			return {
				method: 'press.api.server.change_plan',
				params: {
					name: this.server?.name,
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
				},
				onError(error) {
					this.showChangePlanDialog = false;
					this.$notify({
						title: error,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	},
	methods: {
		plan_title(plan) {
			let india = this.$account.team.country == 'India';
			let currency = india ? '₹' : '$';
			let price_field = india ? 'price_inr' : 'price_usd';
			let price = plan[price_field];
			return price > 0 ? `${currency}${price}` : plan.plan_title;
		}
	},
	computed: {
		plans() {
			let processedPlans = this.$resources.plans.data.map(plan => {
				if (this.plan.name === plan.name) {
					plan.disabled = true;
				}

				return plan;
			});

			return processedPlans;
		},
		used() {
			return this.$resources.usageResource.data;
		},
		usage() {
			return [
				{
					label: 'CPU',
					value: `${this.used.vcpu} / ${this.plan.vcpu} ${this.$plural(
						this.plan.vcpu,
						'vCPU',
						'vCPUs'
					)}`,
					percentage: (this.used.vcpu / this.plan.vcpu) * 100
				},
				{
					label: 'Memory',
					value: `${this.formatBytes(
						this.used.memory,
						0,
						2
					)} / ${this.formatBytes(this.plan.memory, 0, 2)}`,
					percentage: (this.used.memory / this.plan.memory) * 100
				},
				{
					label: 'Storage',
					value: `${this.formatBytes(
						this.used.disk,
						0,
						3
					)} / ${this.formatBytes(this.plan.disk, 0, 3)}`,
					percentage: (this.used.disk / this.plan.disk) * 100
				}
			];
		}
	}
};
</script>
