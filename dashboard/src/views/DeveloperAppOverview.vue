<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<DeveloperAppProfile :app="app" />
		<DeveloperAppLinks :app="app" />
	</div>
</template>

<script>
import DeveloperAppProfile from '@/components/DeveloperAppProfile.vue';
import DeveloperAppLinks from '@/components/DeveloperAppLinks.vue';

export default {
	name: 'DeveloperAppOverview',
	props: {
		app: Object
	},
	components: {
		DeveloperAppProfile,
		DeveloperAppLinks
	}
};
</script>
