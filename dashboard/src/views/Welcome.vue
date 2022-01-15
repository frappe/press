<template>
	<div class="p-8" v-if="$account.onboarding && !$account.onboarding.complete">
		<div class="lg:w-1/2 mx-auto mb-10">
			<Card
				title="Welcome to Frappe Cloud"
				subtitle="To start using Frappe Cloud, complete the following steps to get your account up and running."
			>
				<div class="relative mt-2">
					<OnboardingStepCreateAccount />
					<OnboardingStepSetupPayment
						:active="!$account.onboarding.billing_setup"
						:done="$account.onboarding.billing_setup"
					/>
					<OnboardingStepSelectSitePlan
						v-if="$account.team.via_erpnext"
						:active="$account.onboarding.billing_setup"
						:done="$account.onboarding.erpnext_site_plan_set"
					/>
					<OnboardingStepCreateSite
						v-else
						:active="$account.onboarding.billing_setup"
						:done="$account.onboarding.site_created"
					/>
				</div>
			</Card>
		</div>
	</div>
</template>

<script>
import OnboardingStepCreateAccount from './OnboardingStepCreateAccount.vue';
import OnboardingStepCreateSite from './OnboardingStepCreateSite.vue';
import OnboardingStepSelectSitePlan from './OnboardingStepSelectSitePlan.vue';
import OnboardingStepSetupPayment from './OnboardingStepSetupPayment.vue';
export default {
	name: 'Welcome',
	components: {
		OnboardingStepCreateAccount,
		OnboardingStepSetupPayment,
		OnboardingStepCreateSite,
		OnboardingStepSelectSitePlan
	},
	watch: {
		'$account.onboarding.complete': {
			handler(value) {
				if (value) {
					this.$router.replace('/sites');
				}
			},
			immediate: true
		}
	}
};
</script>
