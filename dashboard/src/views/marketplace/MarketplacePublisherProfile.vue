<template>
	<div>
		<Button
			v-if="$resources.getPublisherProfileInfo.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>

		<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
			<PublisherProfileCard
				:profileData="publisherProfileInfo"
				@profileUpdated="$resources.getPublisherProfileInfo.fetch()"
			/>
		</div>
	</div>
</template>

<script>
import PublisherProfileCard from '@/components/marketplace/PublisherProfileCard.vue';
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
	components: { PublisherProfileCard }
};
</script>
