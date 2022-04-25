<template>
	<div class="mt-8 flex-1">
		<!-- Alerts -->
		<Alert class="mb-4 flex-1" v-if="trial_end_date && $account.needsCard"
			>Your trial ends {{ trialEndsText(trial_end_date) }} after which your site
			will get suspended. Add your billing information to avoid suspension.
			<template #actions>
				<Button class="whitespace-nowrap" route="/saas/billing" type="primary">
					Add Billing Information
				</Button>
			</template>
		</Alert>
		<Alert
			class="mb-4"
			title="Trial"
			v-if="trial_end_date && $account.hasBillingInfo"
		>
			Your trial ends {{ trialEndsInDaysText(trial_end_date) }} after which your
			site will get suspended. Select a plan from the Plan section below to
			avoid suspension.
		</Alert>
		<!-- -->
		<div
			v-if="plansData"
			class="mx-auto grid flex-1 grid-cols-1 gap-2 md:grid-cols-3"
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
import { utils } from '@/utils';

export default {
	name: 'SaasUpgrade',
	components: {
		SaasAppPlanCard
	},
	data() {
		return {
			plansData: null,
			selectedPlan: null,
			activePlan: null,
			trial_end_date: null
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
		plans: {
			method: 'press.api.saas.get_site_sub_info',
			params: {
				site: localStorage.getItem('current_saas_site'),
				app: localStorage.getItem('current_saas_app')
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
