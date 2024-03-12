<template>
	<MarketplaceAppReviewStages
		v-if="$resources.reviewStages"
		:appName="appName"
		:app="app"
		:reviewStages="$resources.reviewStages.data"
	/>
</template>

<script>
import MarketplaceAppReviewStages from '@/components/marketplace/MarketplaceAppReviewStages.vue';

export default {
	name: 'MarketpalceAppReview',
	props: ['appName', 'app'],
	components: {
		MarketplaceAppReviewStages
	},
	resources: {
		reviewStages() {
			return {
				url: 'press.api.marketplace.review_steps',
				params: {
					name: this.appName
				},
				auto: true
			};
		}
	}
};
</script>
