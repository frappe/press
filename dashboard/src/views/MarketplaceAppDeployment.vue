<template>
	<div v-if="app">
		<MarketplaceAppReleaseList :app="app" />
	</div>
</template>

<script>
import MarketplaceAppReleaseList from '@/components/MarketplaceAppReleaseList.vue';

export default {
	name: 'MarketplaceAppDeployment',
	props: {
		app: Object
	},
	components: {
		MarketplaceAppReleaseList
	}
};
</script>
