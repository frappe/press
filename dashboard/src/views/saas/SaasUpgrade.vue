<template>
	<div class="mt-8 flex-1">
		<Alert
			class="flex-1"
			title="Please upgrade plan or else your services with frappeteams will be discontinued from."
		/>
		<div
			v-if="plansData"
			class="mx-auto mt-4 grid flex-1 grid-cols-1 gap-2 md:grid-cols-3"
		>
			<SaasAppPlanCard
				v-for="plan in plansData"
				:plan="plan"
				:key="plan.name"
				:selected="selectedPlan == plan"
				@click.native="handleCardClick(plan)"
			/>
		</div>
		<Button
			v-if="activePlan != selectedPlan"
			class="mt-4"
			type="primary"
			@click="switchToNewPlan()"
			>Change Plan</Button
		>
	</div>
</template>

<script>
import SaasAppPlanCard from './SaasAppPlanCard.vue';

export default {
	name: 'SaasUpgrade',
	components: {
		SaasAppPlanCard
	},
	data() {
		return {
			plansData: null,
			selectedPlan: null,
			activePlan: null
		};
	},
	methods: {
		handleCardClick(plan) {
			this.selectedPlan = plan;
			this.$emit('change', plan);
		},
		switchToNewPlan() {
			this.$resources.changePlan.submit();
		}
	},
	resources: {
		plans: {
			method: 'press.api.saas.get_plans',
			params: {
				site: localStorage.getItem('current_saas_site')
			},
			auto: true,
			onSuccess(result) {
				this.plansData = result;
				this.selectedPlan = result.filter(plan => {
					if (plan.is_selected) {
						return plan;
					}
				})[0];
				this.activePlan = this.selectedPlan;
			}
		},
		changePlan() {
			return {
				method: 'press.api.saas.change_app_plan',
				params: {
					site: localStorage.getItem('current_saas_site'),
					app: this.activePlan,
					new_plan: this.selectedPlan
				},
				onSuccess() {
					this.$resources.plans.reload();
					this.$notify({
						title: 'Plan Changed Successfully!',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	}
};
</script>
