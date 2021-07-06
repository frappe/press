<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<DeveloperAppProfile :app="app" />
	</div>
</template>

<script>
import DeveloperAppProfile from '@/components/DeveloperAppProfile.vue';

export default {
	name: 'DeveloperAppOverview',
	props: {
		app: Object
	},
	components: {
		DeveloperAppProfile
	}
};
</script>
