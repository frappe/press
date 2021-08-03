<template>
	<div>
		<DeveloperAppReleaseList :app="app" />
	</div>
</template>

<script>
import DeveloperAppReleaseList from '@/components/DeveloperAppReleaseList.vue';

export default {
	name: 'DeveloperAppDeployment',
	props: {
		app: Object
	},
	components: {
		DeveloperAppReleaseList
	}
};
</script>
