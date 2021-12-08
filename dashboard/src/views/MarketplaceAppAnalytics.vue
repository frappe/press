<template>
	<div class="sm:grid sm:grid-cols-2">
		<Card title="Installs">
			<div class="divide-y" v-if="analytics">
				<ListItem
					v-for="stat in analytics"
					:key="stat.title"
					:title="stat.title"
					:description="stat.value"
				>
				</ListItem>
			</div>

			<div class="py-10 text-center" v-if="$resources.analytics.loading">
				<Button :loading="true">Loading</Button>
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
	},
	computed: {
		analytics() {
			if (
				!this.$resources.analytics.loading &&
				this.$resources.analytics.data
			) {
				const analyticsData = this.$resources.analytics.data;
				const {
					total_installs,
					num_installs_active_sites,
					num_installs_active_benches
				} = analyticsData;

				return [
					{
						title: 'Total Installs',
						value:
							total_installs.toString() +
							' ' +
							(total_installs == 1 ? 'Site' : 'Sites')
					},
					{
						title: 'Active Sites with this App',
						value:
							num_installs_active_sites.toString() +
							' ' +
							(num_installs_active_sites == 1 ? 'Site' : 'Sites')
					},
					{
						title: 'Active Benches with this App',
						value:
							num_installs_active_benches.toString() +
							' ' +
							(num_installs_active_benches == 1 ? 'Bench' : 'Benches')
					}
				];
			}
		}
	}
};
</script>
