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
		<Dialog title="Change Plan" v-model="showChangePlanDialog">
			<ServerPlansTable
				class="mt-6"
				:plans="plans"
				v-model:selectedPlan="selectedPlan"
			/>
			<ErrorMessage class="mt-4" :error="$resources.changePlan.error" />
			<template #actions>
				<Button @click="showChangePlanDialog = false"> Cancel </Button>
				<Button
					class="ml-2"
					appearance="primary"
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
import ServerPlansTable from '@/components/ServerPlansTable.vue';
export default {
	name: 'ServerOverviewPlan',
	props: ['server', 'plan'],
	components: {
		ServerPlansTable,
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
				method: 'press.api.server.plans',
				params: {
					name: 'Server'
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
		},

		belowCurrentUsage(plan) {
			return this.plan.disk > plan.disk;
		}
	},
	computed: {
		plans() {
			let processedPlans = this.$resources.plans.data.map(plan => {
				console.log(plan.name, plan.disk, this.plan.disk);
				if (this.belowCurrentUsage(plan)) {
					plan.disabled = true;
				}

				if (this.plan.name === plan.name) {
					plan.disabled = true;
				}

				return plan;
			});

			return processedPlans;
		},
	},
	}
};
</script>
