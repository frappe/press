<template>
	<div>
		<div class="mb-4" v-if="activePlan">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-xl font-semibold">Change Plan</h1>
					<p class="text-sm mt-1">{{ app }} plans available for {{ site }}</p>
				</div>
				<Button
					:disabled="activePlan == selectedPlan"
					class="relative top-0 right-0 mb-4"
					type="primary"
					@click="switchToNewPlan()"
					>Change Plan</Button
				>
			</div>
		</div>

		<div
			v-if="plansData"
			class="mx-auto grid flex-1 grid-cols-1 gap-6 md:grid-cols-4"
		>
			<AppPlanCard
				v-for="plan in plansData"
				:plan="plan"
				:key="plan.name"
				:selected="selectedPlan == plan"
				@click.native="handleCardClick(plan)"
			/>
		</div>
	</div>
</template>

<script>
import AppPlanCard from './AppPlanCard.vue';

export default {
	name: 'SubscriptionPlan',
	props: { subName: String, subData: Object },
	components: {
		AppPlanCard
	},
	data() {
		return {
			plansData: null,
			selectedPlan: null,
			activePlan: null,
			trial_end_date: null,
			site: '',
			app: ''
		};
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
			this.$emit('change', plan);
		},
		switchToNewPlan() {
			this.$resources.changePlan.submit();
		},
		trialEndsText(date) {
			return utils.methods.trialEndsInDaysText(date);
		}
	},
	resources: {
		plans() {
			return {
				method: 'press.api.saas.get_plans_info',
				params: {
					name: this.subName
				},
				auto: true,
				onSuccess(result) {
					this.plansData = result.plans;
					this.trial_end_date = result.trial_end_date;
					this.selectedPlan = result.plans.filter(plan => {
						if (plan.is_selected) {
							return plan;
						}
					})[0];
					this.activePlan = this.selectedPlan;
					this.site = result.site;
					this.app = result.app_name;
				}
			};
		},
		changePlan() {
			return {
				method: 'press.api.saas.change_app_plan',
				params: {
					name: this.subName,
					new_plan: this.selectedPlan
				},
				onSuccess() {
					this.$resources.plans.reload();
					this.$notify({
						title: 'Plan Changed Successfully!',
						icon: 'check',
						color: 'green'
					});
				},
				onError(e) {
					this.$notify({
						title: e,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	}
};
</script>
