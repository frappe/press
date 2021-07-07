<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<DeveloperAppProfile :app="app" />
		<DeveloperAppLinks :app="app" />
		<DeveloperAppDescriptions :app="app" />
	</div>
</template>

<script>
import DeveloperAppProfile from '@/components/DeveloperAppProfile.vue';
import DeveloperAppLinks from '@/components/DeveloperAppLinks.vue';
import DeveloperAppDescriptions from '@/components/DeveloperAppDescriptions.vue';

export default {
	name: 'DeveloperAppOverview',
	props: {
		app: Object
	},
	components: {
		DeveloperAppProfile,
		DeveloperAppLinks,
		DeveloperAppDescriptions
	}
};
</script>
