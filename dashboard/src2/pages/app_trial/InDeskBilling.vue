<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="isLoadingInitialData"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div v-else class="px-5 py-8">
		<Onboarding v-if="isOnboardingRequired" />
		<router-view v-else />
	</div>
</template>
<script>
import { setConfig, frappeRequest, createResource } from 'frappe-ui';
import { provide } from 'vue';
import { useRoute } from 'vue-router';
import Onboarding from './in_desk_billing/Onboarding.vue';

export default {
	name: 'In Desk Billing',
	data() {
		return {
			isLoadingInitialTeamData: true,
			isLoadingInitialSiteData: true,
			teamPaymentMode: '',
			isSiteOnTrialPlan: false
		};
	},
	components: {
		Onboarding
	},
	setup() {
		let route = useRoute();
		let request = options => {
			let _options = options || {};
			_options.headers = options.headers || {};
			_options.headers['x-site-access-token'] = route.params.accessToken;
			return frappeRequest(_options);
		};
		setConfig('resourceFetcher', request);
	},
	created() {
		const team = createResource({
			url: '/api/method/press.saas.api.team.info',
			method: 'POST',
			auto: true,
			onSuccess: () => {
				this.isLoadingInitialTeamData = false;
				this.teamPaymentMode = team.data.payment_mode;
			}
		});
		provide('team', team);
		const site = createResource({
			url: '/api/method/press.saas.api.site.info',
			method: 'POST',
			auto: true,
			onSuccess: () => {
				this.isLoadingInitialSiteData = false;
				this.isSiteOnTrialPlan = site.data.plan.is_trial_plan;
			}
		});
		provide('site', site);
	},
	computed: {
		isLoadingInitialData() {
			return this.isLoadingInitialTeamData || this.isLoadingInitialSiteData;
		},
		isOnboardingRequired() {
			if (!this.teamPaymentMode) return true;
			if (this.isSiteOnTrialPlan) return true;
			return false;
		}
	}
};
</script>
