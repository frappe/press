<template>
	<div class="space-y-4">
		<ErrorMessage :error="$resources.analytics.error" />
		<div
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
			v-if="$resources.analytics.data"
		>
			<Card title="Usage Counter">
				<template #actions>
					<router-link
						class="text-base text-blue-500 hover:text-blue-600"
						:to="`/sites/${site.name}/request-logs`"
					>
						View detailed logs →
					</router-link>
				</template>
				<FrappeChart
					type="line"
					:data="usageCounterData"
					:colors="[$theme.colors.purple[500]]"
					:options="getChartOptions(d => d + ' seconds')"
				/>
			</Card>

			<SiteAnalyticsUptime
				:data="$resources.analytics.data.uptime"
				:colors="[$theme.colors.blue[500]]"
			/>

			<Card title="Requests">
				<FrappeChart
					type="line"
					:data="requestCountData"
					:options="getChartOptions(d => d + ' requests')"
					:colors="[$theme.colors.green[500]]"
				/>
			</Card>

			<Card title="CPU Usage">
				<FrappeChart
					type="line"
					:data="requestTimeData"
					:options="getChartOptions(d => d + ' s')"
					:colors="[$theme.colors.yellow[500]]"
				/>
			</Card>
			<Card title="Background Jobs">
				<FrappeChart
					type="line"
					:data="jobCountData"
					:options="getChartOptions(d => d + ' jobs')"
					:colors="[$theme.colors.red[500]]"
				/>
			</Card>
			<Card title="Background Jobs CPU Usage">
				<FrappeChart
					type="line"
					:data="jobTimeData"
					:options="getChartOptions(d => d + ' s')"
					:colors="[$theme.colors.blue[500]]"
				/>
			</Card>
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import FrappeChart from '@/components/FrappeChart.vue';
import SiteAnalyticsUptime from './SiteAnalyticsUptime.vue';

export default {
	name: 'SiteAnalytics',
	props: ['site'],
	components: {
		FrappeChart,
		SiteAnalyticsUptime
	},
	resources: {
		analytics() {
			let localTimezone = DateTime.local().zoneName;
			return {
				method: 'press.api.analytics.get',
				params: {
					name: this.site?.name,
					timezone: localTimezone
				},
				auto: true
			};
		}
	},
	computed: {
		usageCounterData() {
			let data = this.$resources.analytics.data?.usage_counter;
			if (!data) return;

			let plan_limit = this.$resources.analytics.data.plan_limit;
			let values = data.map(d => d.value / 1000000);

			return {
				labels: this.formatDate(data),
				datasets: [{ values }],
				// show daily limit marker if usage crosses 50%
				yMarkers: values.some(value => value > plan_limit / 2)
					? [{ label: 'Daily CPU Time Limit', value: plan_limit }]
					: null
			};
		},
		requestCountData() {
			let requestCount = this.$resources.analytics.data?.request_count;
			if (!requestCount) return;

			return {
				labels: this.formatDate(requestCount),
				datasets: [{ values: requestCount.map(d => d.value) }]
			};
		},
		requestTimeData() {
			let requestCpuTime = this.$resources.analytics.data?.request_cpu_time;
			if (!requestCpuTime) return;

			return {
				labels: this.formatDate(requestCpuTime),
				datasets: [{ values: requestCpuTime.map(d => d.value / 1000000) }]
			};
		},
		jobCountData() {
			let jobCount = this.$resources.analytics.data?.job_count;
			if (!jobCount) return;

			return {
				labels: this.formatDate(jobCount),
				datasets: [{ values: jobCount.map(d => d.value) }]
			};
		},
		jobTimeData() {
			let jobCpuTime = this.$resources.analytics.data?.job_cpu_time;
			if (!jobCpuTime) return;

			return {
				labels: this.formatDate(jobCpuTime),
				datasets: [{ values: jobCpuTime.map(d => d.value / 1000000) }]
			};
		}
	},
	methods: {
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
						return DateTime.fromSQL(d.date).toLocaleString(
							DateTime.DATETIME_MED
						);
					},
					formatTooltipY: yFormatter
				}
			};
		},
		formatDate(data) {
			return data.map(d => ({
				date: d.date,
				toString: () => DateTime.fromSQL(d.date).toFormat('d MMM')
			}));
		}
	}
};
</script>
