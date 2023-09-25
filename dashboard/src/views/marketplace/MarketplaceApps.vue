<template>
	<div>
		<Button
			v-if="$resources.apps.loading && !$resources.apps.data"
			:loading="true"
			loadingText="Loading..."
		></Button>
		<ErrorMessage
			v-else-if="!$resources.apps.data"
			:message="$resources.apps.error"
		/>
		<div v-else-if="$resources.apps.data.length < 1">
			<p class="text-lg text-gray-600">
				You have not published any app on our Marketplace.
			</p>
		</div>
		<div v-else>
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
				<MarketplaceAppCard
					@click.native="routeToAppPage(app.name, app.status)"
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
				url: 'press.api.marketplace.get_apps',
				cache: ['MarketplaceAppList', this.$account.team.name],
				auto: true
			};
		}
	},
	methods: {
		routeToAppPage(appName, status) {
			if (status === 'Draft') {
				this.$router.push(`/marketplace/apps/${appName}/review`);
			} else {
				this.$router.push(`/marketplace/apps/${appName}`);
			}
		}
	}
};
</script>
