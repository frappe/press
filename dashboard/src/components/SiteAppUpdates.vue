<template>
	<div class="space-y-2 divide-y">
		<AppUpdateCard v-for="app in appsWithUpdates" :key="app.app" :app="app" />
		<div
			v-if="!appsWithUpdates.length"
			class="text-center text-base text-gray-500"
		>
			Installed apps doesn't have any updates available. But the site can be
			updated to a newer bench.
		</div>
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
			return this.apps.filter(app => app.update_available);
		}
	}
};
</script>
