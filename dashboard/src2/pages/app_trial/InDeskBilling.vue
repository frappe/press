<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="team.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<router-view v-else />
</template>
<script>
import { setConfig, frappeRequest, createResource } from 'frappe-ui';
import { provide } from 'vue';
import { useRoute } from 'vue-router';

export default {
	name: 'In Desk Billing',
	setup() {
		let request = options => {
			let _options = options || {};
			_options.headers = options.headers || {};
			_options.headers['x-site-access-token'] = useRoute().params.accessToken;
			return frappeRequest(_options);
		};
		setConfig('resourceFetcher', request);
		const team = createResource({
			url: '/api/method/press.saas.api.team.info',
			method: 'POST',
			auto: true
		});
		provide('team', team);
		return {
			team
		};
	}
};
</script>
