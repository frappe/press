<template>
	<div class="sm:grid sm:grid-cols-2">
		<Card title="Installs">
			<div class="divide-y" v-if="this.$resources.analytics.data">
				<ListItem
					title="Total Site Installs"
					:description="`${this.$resources.analytics.data.total_installs}`"
				>
				</ListItem>
				<ListItem
					title="Number of active Sites with this App"
					:description="
						`${this.$resources.analytics.data.num_installs_active_sites}`
					"
				>
				</ListItem>
				<ListItem
					title="Number of active Benches with this App"
					:description="
						`${this.$resources.analytics.data.num_installs_active_benches}`
					"
				>
				</ListItem>
			</div>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'MarketplaceAppAnalytics',
	props: {
		app: Object
	},
	resources: {
		analytics() {
			return {
				method: 'press.api.marketplace.analytics',
				auto: true,
				params: {
					name: this.app.app
				}
			};
		}
	}
};
</script>
