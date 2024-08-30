<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="isLoadingInitialData"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div v-else class="px-5 py-8">
		<router-view />
	</div>
</template>
<script>
import { setConfig, frappeRequest, createResource } from 'frappe-ui';
import { provide } from 'vue';
import { useRoute } from 'vue-router';

export default {
	name: 'In Desk Billing',
	data() {
		return {
			isLoadingInitialTeamData: true,
			isLoadingInitialSiteData: true
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
			onSuccess: () => (this.isLoadingInitialTeamData = false)
		});
		provide('team', team);
		const site = createResource({
			url: '/api/method/press.saas.api.site.info',
			method: 'POST',
			auto: true,
			onSuccess: () => (this.isLoadingInitialSiteData = false)
		});
		provide('site', site);
	},
	computed: {
		isLoadingInitialData() {
			return this.isLoadingInitialTeamData || this.isLoadingInitialSiteData;
		}
	}
};
</script>
