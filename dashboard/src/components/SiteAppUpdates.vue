<template>
	<div class="space-y-2 divide-y">
		<AppUpdateCard v-for="app in appsWithUpdates" :key="app.app" :app="app" />
	</div>
</template>
<script>
import AppUpdateCard from './AppUpdateCard.vue';

export default {
	name: 'SiteAppUpdates',
	props: ['apps'],
	components: {
		AppUpdateCard
	},
	computed: {
		appsWithUpdates() {
			return this.apps.filter((app) => app.update_available);
		}
	}
};
</script>
