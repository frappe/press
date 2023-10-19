<template>
	<div class="space-y-2 divide-y">
		<SiteAppUpdateCard
			v-for="app in appsWithUpdates"
			:key="app.app"
			:app="app"
		/>
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
import SiteAppUpdateCard from './SiteAppUpdateCard.vue';

export default {
	name: 'SiteAppUpdates',
	props: ['apps'],
	components: {
		SiteAppUpdateCard
	},
	computed: {
		appsWithUpdates() {
			return this.apps.filter(app => app.update_available);
		}
	}
};
</script>
