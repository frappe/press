<template>
	<div>
		<Button
			v-if="$resources.getPublisherProfileInfo.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>

		<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
			<PublisherProfileCard :profileData="publisherProfileInfo" />
			<PublisherPayoutInfoCard :profileData="publisherProfileInfo" />
		</div>
	</div>
</template>

<script>
import PublisherProfileCard from '@/components/marketplace/PublisherProfileCard.vue';
import PublisherPayoutInfoCard from '@/components/marketplace/PublisherPayoutInfoCard.vue';

export default {
	data() {
		return {};
	},
	resources: {
		getPublisherProfileInfo() {
			return {
				method: 'press.api.marketplace.get_publisher_profile_info',
				auto: true
			};
		}
	},
	computed: {
		publisherProfileInfo() {
			if (
				this.$resources.getPublisherProfileInfo.loading ||
				!this.$resources.getPublisherProfileInfo.data
			) {
				return;
			}
			return this.$resources.getPublisherProfileInfo.data;
		}
	},
	components: { PublisherProfileCard, PublisherPayoutInfoCard }
};
</script>
