<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="isLoadingInitialData"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div
		v-else-if="isSessionExpired"
		class="flex h-screen w-screen flex-col items-center justify-center gap-4"
	>
		<div class="whitespace-pre-line text-red-600" role="alert">
			Session Expired. Refresh the page.
		</div>
	</div>
	<div v-else>
		<Onboarding v-if="isOnboardingRequired" />
		<TabsWithRouter v-else :tabs="tabs" />
	</div>
</template>
<style>
[role='tablist'] {
	padding-left: 0px !important;
}

.transition-opacity {
	transition-property: none !important;
	transition-duration: 0s !important;
	transition-timing-function: unset !important;
}
</style>
<script>
import { setConfig, frappeRequest, createResource } from 'frappe-ui';
import { provide } from 'vue';
import { useRoute } from 'vue-router';
import Onboarding from './in_desk_billing/Onboarding.vue';
import { Tabs, Breadcrumbs } from 'frappe-ui';
import Header from '../../components/Header.vue';
import TabsWithRouter from '../../components/TabsWithRouter.vue';

export default {
	name: 'In Desk Billing',
	components: {
		Onboarding,
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter
	},
	data() {
		return {
			isLoadingInitialTeamData: true,
			isLoadingInitialSiteData: true,
			teamPaymentMode: '',
			isSiteOnTrialPlan: false,
			isSessionExpired: false,
			// Tab data
			currentTab: 0,
			tabs: [
				{ label: 'Overview', route: { name: 'IntegratedBillingOverview' } },
				{ label: 'Invoices', route: { name: 'IntegratedBillingInvoices' } }
			]
		};
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
	mounted() {
		setInterval(this.isAccessTokenValid, 10000);
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
	},
	methods: {
		isAccessTokenValid() {
			const accesstoken = this.$route?.params?.accessToken;
			if (!accesstoken) return;
			fetch(`/api/method/press.saas.api.auth.is_access_token_valid`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					token: accesstoken
				})
			})
				.then(response => response.json())
				.then(data => {
					this.isSessionExpired = !(data?.message ?? true);
				})
				.catch(console.error);
		}
	}
};
</script>
