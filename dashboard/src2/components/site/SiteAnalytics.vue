<template>
	<div class="space-y-4 p-5">
		<div class="flex space-x-4">
			<FormControl
				class="ml-auto w-32"
				type="select"
				:options="durationOptions"
				v-model="duration"
			/>
		</div>
		<ErrorMessage
			:message="
				$resources.analytics.error || $resources.advancedAnalytics.error
			"
		/>

		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<AnalyticsCard title="Daily Usage">
				<LineChart
					type="time"
					title="Usage Counter"
					:key="usageCounterData"
					:data="usageCounterData"
					unit="seconds"
					:chartTheme="[$theme.colors.purple[500]]"
					:loading="$resources.analytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Uptime">
				<SiteUptime
					:data="$resources.analytics?.data?.uptime"
					:loading="$resources.analytics.loading"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Requests">
				<LineChart
					type="time"
					title="Requests"
					:key="requestCountData"
					:data="requestCountData"
					unit="requests"
					:chartTheme="[$theme.colors.green[500]]"
					:loading="$resources.analytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
				<template #action>
					<router-link
						class="text-base text-gray-600 hover:text-gray-700"
						:to="{ name: 'Site Performance Request Logs' }"
					>
						Request Log Report →
					</router-link>
				</template>
			</AnalyticsCard>

			<AnalyticsCard title="Requests CPU Usage">
				<LineChart
					type="time"
					title="Requests CPU Usage"
					:key="requestTimeData"
					:data="requestTimeData"
					unit="seconds"
					:chartTheme="[$theme.colors.yellow[500]]"
					:loading="$resources.analytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>

		<div class="!mt-6 flex space-x-2">
			<h2 class="text-lg font-semibold">Advanced Analytics</h2>
			<FeatherIcon
				class="h-5 w-5 cursor-pointer text-gray-500 hover:text-gray-700"
				:name="showAdvancedAnalytics ? 'chevron-down' : 'chevron-right'"
				@click="toggleAdvancedAnalytics"
			/>
		</div>

		<!-- Advanced Analytics -->
		<div
			v-if="showAdvancedAnalytics"
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
		>
			<AnalyticsCard title="Background Jobs">
				<LineChart
					type="time"
					title="Background Jobs"
					:key="jobCountData"
					:data="jobCountData"
					unit="jobs"
					:chartTheme="[$theme.colors.red[500]]"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Background Jobs CPU Usage">
				<LineChart
					type="time"
					title="Background Jobs CPU Usage"
					:key="jobTimeData"
					:data="jobTimeData"
					unit="seconds"
					:chartTheme="[$theme.colors.blue[500]]"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Frequent Requests">
				<BarChart
					title="Request Count by Path"
					:key="requestCountByPathData"
					:data="requestCountByPathData"
					unit="requests"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Slowest Requests">
				<BarChart
					:key="requestDurationByPathData"
					:data="requestDurationByPathData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Individual Request Time (Average)"
			>
				<BarChart
					:key="averageRequestDurationByPathData"
					:data="averageRequestDurationByPathData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Frequent Background Jobs">
				<BarChart
					:key="backgroundJobCountByMethodData"
					:data="backgroundJobCountByMethodData"
					unit="jobs"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Slowest Background Jobs">
				<BarChart
					:key="backgroundJobDurationByMethodData"
					:data="backgroundJobDurationByMethodData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Individual Background Job Time (Average)"
			>
				<BarChart
					:key="averageBackgroundJobDurationByMethodData"
					:data="averageBackgroundJobDurationByMethodData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Frequent Slow Queries">
				<BarChart
					:key="slowLogsByCountData"
					:data="slowLogsByCountData"
					unit="queries"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
				<template #action>
					<router-link
						class="text-base text-gray-600 hover:text-gray-700"
						:to="{ name: 'Site Performance Slow Queries' }"
					>
						Slow Queries Reports →
					</router-link>
				</template>
			</AnalyticsCard>

			<AnalyticsCard class="sm:col-span-2" title="Top Slow Queries">
				<BarChart
					:key="slowLogsByDurationData"
					:data="slowLogsByDurationData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>
		</div>
	</div>
</template>

<script>
import dayjs from '../../utils/dayjs';
import LineChart from '@/components/charts/LineChart.vue';
import BarChart from '@/components/charts/BarChart.vue';
import SiteUptime from './SiteUptime.vue';
import AlertBanner from '../AlertBanner.vue';
import AnalyticsCard from './AnalyticsCard.vue';

export default {
	name: 'SiteAnalytics',
	props: ['name'],
	components: {
		BarChart,
		LineChart,
		SiteUptime,
		AlertBanner,
		AnalyticsCard
	},
	data() {
		return {
			duration: '24h',
			showAdvancedAnalytics: false,
			durationOptions: [
				{ label: 'Duration', value: null, disabled: true },
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
			const localTimezone = dayjs.tz.guess();
			return {
				url: 'press.api.analytics.get',
				params: {
					name: this.name,
					timezone: localTimezone,
					duration: this.duration
				},
				auto: true
			};
		},
		advancedAnalytics() {
			const localTimezone = dayjs.tz.guess();
			return {
				url: 'press.api.analytics.get_advanced_analytics',
				params: {
					name: this.name,
					timezone: localTimezone,
					duration: this.duration
				},
				auto: this.showAdvancedAnalytics
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
				this.$resources.advancedAnalytics.data?.request_count_by_path;
			if (!requestCountByPath) return;

			return requestCountByPath;
		},
		requestDurationByPathData() {
			let requestDurationByPath =
				this.$resources.advancedAnalytics.data?.request_duration_by_path;
			if (!requestDurationByPath) return;

			return requestDurationByPath;
		},
		averageRequestDurationByPathData() {
			let averageRequestDurationByPath =
				this.$resources.advancedAnalytics.data
					?.average_request_duration_by_path;
			if (!averageRequestDurationByPath) return;

			return averageRequestDurationByPath;
		},
		backgroundJobCountByMethodData() {
			let backgroundJobCountByMethod =
				this.$resources.advancedAnalytics.data?.background_job_count_by_method;
			if (!backgroundJobCountByMethod) return;

			return backgroundJobCountByMethod;
		},
		backgroundJobDurationByMethodData() {
			let backgroundJobDurationByMethod =
				this.$resources.advancedAnalytics.data
					?.background_job_duration_by_method;
			if (!backgroundJobDurationByMethod) return;

			return backgroundJobDurationByMethod;
		},
		averageBackgroundJobDurationByMethodData() {
			let averageBackgroundJobDurationByMethod =
				this.$resources.advancedAnalytics.data
					?.average_background_job_duration_by_method;
			if (!averageBackgroundJobDurationByMethod) return;

			return averageBackgroundJobDurationByMethod;
		},
		slowLogsByCountData() {
			let slowLogsByCount =
				this.$resources.advancedAnalytics.data?.slow_logs_by_count;
			if (!slowLogsByCount) return;

			return slowLogsByCount;
		},
		slowLogsByDurationData() {
			let slowLogsByDuration =
				this.$resources.advancedAnalytics.data?.slow_logs_by_duration;
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
			let jobCount = this.$resources.advancedAnalytics.data?.job_count;
			if (!jobCount) return;

			return {
				datasets: [jobCount.map(d => [+new Date(d.date), d.value])]
			};
		},
		jobTimeData() {
			let jobCpuTime = this.$resources.advancedAnalytics.data?.job_cpu_time;
			if (!jobCpuTime) return;

			return {
				datasets: [jobCpuTime.map(d => [+new Date(d.date), d.value / 1000000])]
			};
		}
	},
	methods: {
		toggleAdvancedAnalytics() {
			this.showAdvancedAnalytics = !this.showAdvancedAnalytics;
		}
	}
};
</script>
