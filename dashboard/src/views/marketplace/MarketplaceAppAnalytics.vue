<template>
	<div class="sm:grid gap-5 sm:grid-cols-2">
		<Card title="Pageviews">
			<template #actions>
				<a
					v-if="app"
					class="text-base text-blue-500 hover:text-blue-600"
					:href="`/marketplace/apps/${app.app}`"
					target="_blank"
				>
					View Marketplace Page →
				</a>
			</template>
			<FrappeChart
				v-if="$resources.plausible_analytics.data"
				type="line"
				:data="pageViewsData"
				:options="getChartOptions(d => d + ' views')"
				:colors="[$theme.colors.purple[500]]"
			/>
			<LoadingText v-if="$resources.plausible_analytics.loading" />
			<ErrorMessage
				v-if="$resources.plausible_analytics.error"
				:message="$resources.plausible_analytics.error"
			/>
		</Card>
		<Card title="Unique Visitors">
			<FrappeChart
				v-if="$resources.plausible_analytics.data"
				type="line"
				:data="visitorsData"
				:options="getChartOptions(d => d + ' visitors')"
				:colors="[$theme.colors.green[500]]"
			/>
			<LoadingText v-if="$resources.plausible_analytics.loading" />
		</Card>
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
import { DateTime } from 'luxon';
import FrappeChart from '@/components/FrappeChart.vue';

export default {
	name: 'MarketplaceAppAnalytics',
	props: {
		app: Object
	},
	components: {
		FrappeChart
	},
	methods: {
		formatDate(data) {
			return data.map(d => d.date);
		},
		getChartOptions(yFormatter) {
			return {
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true,
					regionFill: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromISO(d).toLocaleString(DateTime.DATE_MED);
					},
					formatTooltipY: yFormatter
				}
			};
		}
	},
	resources: {
		analytics() {
			return {
				method: 'press.api.marketplace.analytics',
				auto: true,
				params: {
					name: this.app?.app
				}
			};
		},
		plausible_analytics() {
			return {
				method: 'press.api.analytics.plausible_analytics',
				auto: true,
				params: {
					name: this.app?.app
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
		},
		pageViewsData() {
			let pageViews = this.$resources.plausible_analytics.data?.pageviews;
			if (!pageViews) return;

			let values = pageViews.map(d => d.value);

			return {
				labels: this.formatDate(pageViews),
				datasets: [{ values }]
			};
		},
		visitorsData() {
			let visitorsData = this.$resources.plausible_analytics.data?.visitors;
			if (!visitorsData) return;

			let values = visitorsData.map(d => d.value);

			return {
				labels: this.formatDate(visitorsData),
				datasets: [{ values }]
			};
		}
	}
};
</script>
