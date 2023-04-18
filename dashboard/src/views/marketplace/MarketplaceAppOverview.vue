<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2" v-if="app">
		<MarketplaceAppProfile :app="app" />
		<MarketplaceAppLinks :app="app" />
		<MarketplaceAppScreenshots :app="app" />
		<MarketplaceAppDescriptions :app="app" />
	</div>
</template>

<script>
import MarketplaceAppProfile from '@/components/MarketplaceAppProfile.vue';
import MarketplaceAppLinks from '@/components/MarketplaceAppLinks.vue';
import MarketplaceAppDescriptions from '@/components/MarketplaceAppDescriptions.vue';
import MarketplaceAppScreenshots from '@/components/MarketplaceAppScreenshots.vue';

export default {
	name: 'MarketplaceAppOverview',
	props: {
		app: Object
	},
	components: {
		MarketplaceAppProfile,
		MarketplaceAppLinks,
		MarketplaceAppDescriptions,
		MarketplaceAppScreenshots
	}
};
</script>
