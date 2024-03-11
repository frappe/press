<template>
	<div class="space-y-4">
		<ErrorMessage :message="$resources.analytics.error" />
		<FormControl
			class="w-32"
			label="Duration"
			type="select"
			:options="durationOptions"
			v-model="duration"
		/>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<LineChart
				type="time"
				title="Usage Counter"
				:key="usageCounterData"
				:data="usageCounterData"
				unit="seconds"
				:chartTheme="[$theme.colors.purple[500]]"
				:loading="$resources.analytics.loading"
			/>

			<SiteAnalyticsUptime
				:data="$resources.analytics?.data?.uptime"
				:loading="$resources.analytics.loading"
			/>

			<LineChart
				type="time"
				title="Requests"
				:key="requestCountData"
				:data="requestCountData"
				unit="requests"
				:chartTheme="[$theme.colors.green[500]]"
				:loading="$resources.analytics.loading"
			/>
			<LineChart
				type="time"
				title="CPU Usage"
				:key="requestTimeData"
				:data="requestTimeData"
				unit="seconds"
				:chartTheme="[$theme.colors.yellow[500]]"
				:loading="$resources.analytics.loading"
			/>
			<LineChart
				type="time"
				title="Background Jobs"
				:key="jobCountData"
				:data="jobCountData"
				unit="jobs"
				:chartTheme="[$theme.colors.red[500]]"
				:loading="$resources.analytics.loading"
			/>
			<LineChart
				type="time"
				title="Background Jobs CPU Usage"
				:key="jobTimeData"
				:data="jobTimeData"
				unit="seconds"
				:chartTheme="[$theme.colors.blue[500]]"
				:loading="$resources.analytics.loading"
			/>

			<BarChart
				class="sm:col-span-2"
				title="Request Count by Path"
				:key="requestCountByPathData"
				:data="requestCountByPathData"
				unit="requests"
				:chartTheme="requestChartColors"
				:loading="$resources.analytics.loading"
			/>
			<BarChart
				class="sm:col-span-2"
				title="Request Duration by Path"
				:key="requestDurationByPathData"
				:data="requestDurationByPathData"
				unit="seconds"
				:chartTheme="requestChartColors"
				:loading="$resources.analytics.loading"
			/>
			<BarChart
				class="sm:col-span-2"
				title="Average Request Duration by Path"
				:key="averageRequestDurationByPathData"
				:data="averageRequestDurationByPathData"
				unit="seconds"
				:chartTheme="requestChartColors"
				:loading="$resources.analytics.loading"
			/>
			<BarChart
				class="sm:col-span-2"
				title="Slow Logs by Count"
				:key="slowLogsByCountData"
				:data="slowLogsByCountData"
				unit="queries"
				:chartTheme="requestChartColors"
				:loading="$resources.analytics.loading"
			/>
			<BarChart
				class="sm:col-span-2"
				title="Slow Logs by Duration"
				:key="slowLogsByDurationData"
				:data="slowLogsByDurationData"
				unit="seconds"
				:chartTheme="requestChartColors"
				:loading="$resources.analytics.loading"
			/>
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import LineChart from '@/components/charts/LineChart.vue';
import BarChart from '@/components/charts/BarChart.vue';
import SiteAnalyticsUptime from './SiteAnalyticsUptime.vue';

export default {
	name: 'SiteAnalytics',
	props: ['siteName'],
	components: {
		BarChart,
		LineChart,
		SiteAnalyticsUptime
	},
	data() {
		return {
			duration: '7d',
			durationOptions: [
				{ label: '1 hour', value: '1h' },
				{ label: '6 hours', value: '6h' },
				{ label: '24 hours', value: '24h' },
				{ label: '7 days', value: '7d' },
				{ label: '15 days', value: '15d' }
			]
		};
	},
	resources: {
		analytics() {
			let localTimezone = DateTime.local().zoneName;
			return {
				url: 'press.api.analytics.get',
				params: {
					name: this.siteName,
					timezone: localTimezone,
					duration: this.duration
				},
				auto: true
			};
		}
	},
	computed: {
		requestChartColors() {
			return [
				this.$theme.colors.green[500],
				this.$theme.colors.red[500],
				this.$theme.colors.yellow[500],
				this.$theme.colors.pink[500],
				this.$theme.colors.purple[500],
				this.$theme.colors.blue[500],
				this.$theme.colors.teal[500],
				this.$theme.colors.cyan[500],
				this.$theme.colors.gray[500],
				this.$theme.colors.orange[500]
			];
		},
		usageCounterData() {
			let data = this.$resources.analytics.data?.usage_counter;
			if (!data) return;

			let plan_limit = this.$resources.analytics.data?.plan_limit;

			return {
				datasets: [data.map(d => [+new Date(d.date), d.value / 1000000])],
				// daily limit marker
				markLine: {
					data: [
						{
							name: 'Daily Compute Limit',
							yAxis: plan_limit,
							label: {
								formatter: '{b}: {c} seconds',
								position: 'middle'
							},
							lineStyle: {
								color: '#f5222d'
							}
						}
					],
					symbol: ['none', 'none']
				}
			};
		},
		requestCountData() {
			let requestCount = this.$resources.analytics.data?.request_count;
			if (!requestCount) return;

			return {
				datasets: [requestCount.map(d => [+new Date(d.date), d.value])]
			};
		},
		requestCountByPathData() {
			let requestCountByPath =
				this.$resources.analytics.data?.request_count_by_path;
			if (!requestCountByPath) return;

			return requestCountByPath;
		},
		requestDurationByPathData() {
			let requestDurationByPath =
				this.$resources.analytics.data?.request_duration_by_path;
			if (!requestDurationByPath) return;

			return requestDurationByPath;
		},
		averageRequestDurationByPathData() {
			let averageRequestDurationByPath =
				this.$resources.analytics.data?.average_request_duration_by_path;
			if (!averageRequestDurationByPath) return;

			return averageRequestDurationByPath;
		},
		slowLogsByCountData() {
			let slowLogsByCount = this.$resources.analytics.data?.slow_logs_by_count;
			if (!slowLogsByCount) return;

			return slowLogsByCount;
		},
		slowLogsByDurationData() {
			let slowLogsByDuration =
				this.$resources.analytics.data?.slow_logs_by_duration;
			if (!slowLogsByDuration) return;

			return slowLogsByDuration;
		},
		requestTimeData() {
			let requestCpuTime = this.$resources.analytics.data?.request_cpu_time;
			if (!requestCpuTime) return;

			return {
				datasets: [
					requestCpuTime.map(d => [+new Date(d.date), d.value / 1000000])
				]
			};
		},
		jobCountData() {
			let jobCount = this.$resources.analytics.data?.job_count;
			if (!jobCount) return;

			return {
				datasets: [jobCount.map(d => [+new Date(d.date), d.value])]
			};
		},
		jobTimeData() {
			let jobCpuTime = this.$resources.analytics.data?.job_cpu_time;
			if (!jobCpuTime) return;

			return {
				datasets: [jobCpuTime.map(d => [+new Date(d.date), d.value / 1000000])]
			};
		}
	}
};
</script>
