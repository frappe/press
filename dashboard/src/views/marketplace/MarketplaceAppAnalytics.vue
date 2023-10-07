<template>
	<div
		v-if="$resources.analytics.data"
		class="grid grid-cols-1 gap-5 sm:grid-cols-2"
	>
		<Card title="Earnings">
			<template #actions>
				<a
					class="text-base text-blue-500 hover:text-blue-600"
					href="/support/tickets"
					target="_blank"
				>
					Contact Support →
				</a>
			</template>
			<ListItem
				title="Total Earnings"
				:subtitle="`Total earnings for ${app.title}`"
			>
				<template #actions>
					<span class="text-base font-semibold text-green-500">{{
						'$' +
						paymentAnalytics.total_payout.usd +
						' + ' +
						'₹' +
						paymentAnalytics.total_payout.inr
					}}</span>
				</template>
			</ListItem>
			<ListItem
				title="Pending Payout"
				subtitle="Payout you are yet to receive from Frappe Cloud"
			>
				<template #actions>
					<span class="text-base font-semibold">{{
						'$' +
						paymentAnalytics.pending_payout.usd +
						' + ' +
						'₹' +
						paymentAnalytics.pending_payout.inr
					}}</span>
				</template>
			</ListItem>
			<ListItem
				title="Commission"
				subtitle="Payouts start once you have passed $500 threshold"
			>
				<template #actions>
					<span class="text-base font-semibold">{{
						'$' +
						paymentAnalytics.commission.usd +
						' + ' +
						'₹' +
						paymentAnalytics.commission.inr
					}}</span>
				</template>
			</ListItem>
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
		<LineChart
			title="Pageviews"
			type="time"
			:key="pageViewsData"
			:data="pageViewsData"
			unit="views"
			:chartTheme="$theme.colors.purple[500]"
			:loading="$resources.plausible_analytics.loading"
			:error="$resources.plausible_analytics.error"
		>
			<template #actions>
				<a
					v-if="app"
					class="text-base text-gray-700 hover:text-gray-800"
					:href="`/marketplace/apps/${app.app}`"
					target="_blank"
				>
					View Marketplace Page →
				</a>
			</template>
		</LineChart>
		<LineChart
			title="Unique Visitors"
			type="time"
			:key="visitorsData"
			:data="visitorsData"
			unit="visitors"
			:chartTheme="$theme.colors.green[500]"
			:loading="$resources.plausible_analytics.loading"
			:error="$resources.plausible_analytics.error"
		/>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import LineChart from '@/components/charts/LineChart.vue';

export default {
	name: 'MarketplaceAppAnalytics',
	props: {
		app: Object
	},
	components: {
		LineChart
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
				url: 'press.api.marketplace.analytics',
				auto: true,
				params: {
					name: this.app?.app
				}
			};
		},
		plausible_analytics() {
			return {
				url: 'press.api.analytics.plausible_analytics',
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

			return {
				datasets: pageViews.map(d => [+new Date(d.date), d.value])
			};
		},
		visitorsData() {
			let visitorsData = this.$resources.plausible_analytics.data?.visitors;
			if (!visitorsData) return;

			return {
				datasets: visitorsData.map(d => [+new Date(d.date), d.value])
			};
		},
		paymentAnalytics() {
			if (
				!this.$resources.analytics.loading &&
				this.$resources.analytics.data
			) {
				let data = this.$resources.analytics.data;
				return {
					total_payout: {
						usd: data.total_payout.usd_amount
							? data.total_payout.usd_amount.toFixed(2)
							: 0.0,
						inr: data.total_payout.inr_amount
							? data.total_payout.inr_amount.toFixed(2)
							: 0.0
					},
					pending_payout: {
						usd: data.pending_payout.usd_amount
							? data.pending_payout.usd_amount.toFixed(2)
							: 0.0,
						inr: data.pending_payout.inr_amount
							? data.pending_payout.inr_amount.toFixed(2)
							: 0.0
					},
					commission: {
						usd: data.commission.usd_amount
							? data.commission.usd_amount.toFixed(2)
							: 0.0,
						inr: data.commission.inr_amount
							? data.commission.inr_amount.toFixed(2)
							: 0.0
					}
				};
			}
		}
	}
};
</script>
