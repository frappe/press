<template>
	<div>
		<Button
			v-if="$resources.apps.loading"
			:loading="true"
			loadingText="Loading..."
		></Button>
		<ErrorMessage
			v-else-if="!$resources.apps.data"
			:error="$resources.apps.error"
		/>
		<div v-else-if="$resources.apps.data.length < 1">
			<p class="text-lg text-gray-600">
				You have not published any app on our Marketplace.
			</p>
		</div>
		<div v-else>
			<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
				<MarketplaceAppCard
					@click.native="routeToAppPage(app.name)"
					v-for="app in $resources.apps.data"
					:key="app.name"
					:app="app"
				/>
			</div>
		</div>
	</div>
</template>

<script>
import MarketplaceAppCard from '@/components/MarketplaceAppCard.vue';

export default {
	name: 'MarketplaceApps',
	components: {
		MarketplaceAppCard
	},
	activated() {
		this.$resources.apps.fetch();
	},
	resources: {
		apps() {
			return {
				method: 'press.api.marketplace.get_apps',
				auto: true
			};
		}
	},
	methods: {
		routeToAppPage(appName) {
			this.$router.push(`/marketplace/apps/${appName}`);
		}
	}
};
</script>
