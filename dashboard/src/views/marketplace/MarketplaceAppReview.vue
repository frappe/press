<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<MarketplaceAppReviewStages 
			v-if="$resources.reviewStages"
			:appName="appName"
			:app="app"
			:reviewStages="$resources.reviewStages.data"
		/>
	</div>
</template>

<script>
import MarketplaceAppReviewStages from '@/components/marketplace/MarketplaceAppReviewStages.vue';

export default {
	name: 'MarketpalceAppReview',
	props: ['appName', 'app'],
	components: {
		MarketplaceAppReviewStages,
	},
	resources: {
		reviewStages() {
			return {
				method: 'press.api.marketplace.review_stages',
				params: {
					name: this.appName,
				},
				auto: true,
			}
		}
	}
}
</script>
