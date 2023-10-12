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
		</div>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import LineChart from '@/components/charts/LineChart.vue';
import SiteAnalyticsUptime from './SiteAnalyticsUptime.vue';

export default {
	name: 'SiteAnalytics',
	props: ['site'],
	components: {
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
					name: this.site?.name,
					timezone: localTimezone,
					duration: this.duration
				},
				auto: true
			};
		}
	},
	computed: {
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
