<template>
	<div
		class="flex flex-col justify-end items-center sticky top-0 z-20 p-3 px-5 w-full bg-white border-b justify-self-center space-y-2"
	>
		<div class="flex space-x-4 w-full">
			<!-- Group all content items so spacing is consistent -->
			<div class="flex space-x-4 w-full">
				<!-- Start date group -->
				<div class="flex space-x-2">
					<label class="text-base text-gray-600 self-center whitespace-nowrap">
						Absolute <span class="text-black">from</span>
					</label>
					<DateTimePicker
						:modelValue="inputStartDate"
						variant="subtle"
						label="Start date"
						:disabled="false"
						:formatter="dateFormatter"
						@update:modelValue="updateStartDate"
					/>
				</div>

				<!-- End date group -->
				<div class="flex space-x-2">
					<label class="text-base self-center">to</label>
					<DateTimePicker
						:modelValue="inputEndDate"
						variant="subtle"
						label="End date"
						:disabled="false"
						:formatter="dateFormatter"
						@update:modelValue="updateEndDate"
					/>
				</div>

				<!-- Divider -->
				<div class="w-px bg-gray-200" />

				<!-- Duration group -->
				<div class="flex space-x-2">
					<label class="text-base self-center text-gray-600">Relative</label>
					<FormControl
						type="select"
						class="w-32"
						:options="durationOptions"
						v-model="duration"
					/>
				</div>

				<!-- Grow -->
				<div class="flex-grow" />

				<Tooltip text="Copy a shareable link to this Dashboard">
					<!-- Share button -->
					<ActionButton
						variant="subtle"
						label="Share"
						class="text-gray-300 hover:text-black duration-200"
						@click="(e) => shareDashboard(e, `global`)"
						:slots="{
							prefix: shareDashboardActionPrefix,
						}"
					/>
				</Tooltip>
			</div>
		</div>

		<div v-if="!!dateRangeError" class="text-red-500 text-sm">
			{{ dateRangeError }}
		</div>
	</div>
	<div class="space-y-4 p-5">
		<ErrorMessage
			:message="
				$resources.analytics.error || $resources.advancedAnalytics.error
			"
		/>

		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<AnalyticsCard title="Daily Usage" @share-card="shareDashboard">
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

			<AnalyticsCard title="Uptime" @share-card="shareDashboard">
				<SiteUptime
					:data="$resources.analytics?.data?.uptime"
					:loading="$resources.analytics.loading"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard title="Requests" @share-card="shareDashboard">
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

			<AnalyticsCard title="Requests CPU Usage" @share-card="shareDashboard">
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

		<div
			class="!mt-6 flex w-fit cursor-pointer space-x-2"
			@click="toggleAdvancedAnalytics"
		>
			<h2 class="text-lg font-semibold">Advanced Analytics</h2>
			<FeatherIcon
				class="h-5 w-5 text-gray-500 hover:text-gray-700"
				:name="showAdvancedAnalytics ? 'chevron-down' : 'chevron-right'"
			/>
		</div>

		<!-- Advanced Analytics -->
		<div
			v-if="showAdvancedAnalytics"
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
		>
			<AnalyticsCard title="Background Jobs" @share-card="shareDashboard">
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

			<AnalyticsCard
				title="Background Jobs CPU Usage"
				@share-card="shareDashboard"
			>
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

			<AnalyticsCard
				class="sm:col-span-2"
				title="Frequent Requests"
				@share-card="shareDashboard"
			>
				<BarChart
					title="Request Count by Path"
					:key="requestCountByPathData"
					:data="requestCountByPathData"
					unit="requests"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Slowest Requests"
				@share-card="shareDashboard"
			>
				<BarChart
					:key="requestDurationByPathData"
					:data="requestDurationByPathData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Query Report Durations"
				v-if="queryReportRunReportsData"
				@share-card="shareDashboard"
			>
				<template #action>
					<Tooltip text="Shown only as reports seem to take time">
						<lucide-info class="ml-2 mr-auto h-3.5 w-3.5 text-gray-500" />
					</Tooltip>
				</template>
				<BarChart
					:key="queryReportRunReportsData"
					:data="queryReportRunReportsData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Run Doc Method Durations"
				v-if="runDocMethodMethodnamesData"
				@share-card="shareDashboard"
			>
				<template #action>
					<Tooltip text="Shown only as run_doc_method calls seem to take time">
						<lucide-info class="ml-2 mr-auto h-3.5 w-3.5 text-gray-500" />
					</Tooltip>
				</template>
				<BarChart
					:key="runDocMethodMethodnamesData"
					:data="runDocMethodMethodnamesData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Save Docs Doctype Durations"
				v-if="saveDocsDoctypesData"
			>
				<template #action>
					<Tooltip text="Shown only as savedocs calls seem to take time">
						<lucide-info class="ml-2 mr-auto h-3.5 w-3.5 text-gray-500" />
					</Tooltip>
				</template>
				<BarChart
					:key="saveDocsDoctypesData"
					:data="saveDocsDoctypesData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Save Docs Action Durations"
				v-if="saveDocsActionData"
			>
				<template #action>
					<Tooltip text="Shown only as savedocs calls seem to take time">
						<lucide-info class="ml-2 mr-auto h-3.5 w-3.5 text-gray-500" />
					</Tooltip>
				</template>
				<BarChart
					:key="saveDocsActionData"
					:data="saveDocsActionData"
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
				@share-card="shareDashboard"
			>
				<BarChart
					:key="averageRequestDurationByPathData"
					:data="averageRequestDurationByPathData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>
			<AnalyticsCard
				class="sm:col-span-2"
				title="Requests by IP"
				@share-card="shareDashboard"
			>
				<BarChart
					:key="requestCountByIPData"
					:data="requestCountByIPData"
					unit="requests"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Frequent Background Jobs"
				@share-card="shareDashboard"
			>
				<BarChart
					:key="backgroundJobCountByMethodData"
					:data="backgroundJobCountByMethodData"
					unit="jobs"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Slowest Background Jobs"
				@share-card="shareDashboard"
			>
				<BarChart
					:key="backgroundJobDurationByMethodData"
					:data="backgroundJobDurationByMethodData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Background Report Durations"
				v-if="generateReportReportsData"
				@share-card="shareDashboard"
			>
				<template #action>
					<Tooltip text="Shown only as reports seem to take time">
						<lucide-info class="ml-2 mr-auto h-3.5 w-3.5 text-gray-500" />
					</Tooltip>
				</template>
				<BarChart
					:key="generateReportReportsData"
					:data="generateReportReportsData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Individual Background Job Time (Average)"
				@share-card="shareDashboard"
			>
				<BarChart
					:key="averageBackgroundJobDurationByMethodData"
					:data="averageBackgroundJobDurationByMethodData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.advancedAnalytics.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Frequent Slow Queries"
				@share-card="shareDashboard"
			>
				<template #action>
					<Tooltip text="Show Detailed Reports">
						<router-link
							class="mr-auto text-base text-gray-600 hover:text-gray-700"
							:to="{ name: 'Site Performance Slow Queries' }"
						>
							→
						</router-link>
					</Tooltip>
					<TabButtons
						:buttons="[{ label: 'Denormalized' }, { label: 'Normalized' }]"
						v-model="slowLogsFrequencyType"
					/>
				</template>
				<BarChart
					:key="slowLogsCountData"
					:data="slowLogsCountData"
					unit="queries"
					:chartTheme="requestChartColors"
					:loading="$resources.slowLogsCount.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>

			<AnalyticsCard
				class="sm:col-span-2"
				title="Top Slow Queries"
				@share-card="shareDashboard"
			>
				<template #action>
					<Tooltip text="Show Detailed Reports">
						<router-link
							class="mr-auto text-base text-gray-600 hover:text-gray-700"
							:to="{ name: 'Site Performance Slow Queries' }"
						>
							→
						</router-link>
					</Tooltip>
					<TabButtons
						:buttons="[{ label: 'Denormalized' }, { label: 'Normalized' }]"
						v-model="slowLogsDurationType"
					/>
				</template>
				<BarChart
					:key="slowLogsDurationData"
					:data="slowLogsDurationData"
					unit="seconds"
					:chartTheme="requestChartColors"
					:loading="$resources.slowLogsDuration.loading"
					:showCard="false"
					class="h-[15.55rem] p-2 pb-3"
					@datazoom="handleDataZoom"
				/>
			</AnalyticsCard>
		</div>
	</div>
</template>

<script>
import { TabButtons, DateTimePicker, Button, Tooltip } from 'frappe-ui';
import { toast } from 'vue-sonner';
import dayjs from '../../utils/dayjs';
import LineChart from '@/components/charts/LineChart.vue';
import BarChart from '@/components/charts/BarChart.vue';
import SiteUptime from './SiteUptime.vue';
import AlertBanner from '../AlertBanner.vue';
import AnalyticsCard from './AnalyticsCard.vue';
import ShareIcon from '../icons/ShareIcon.vue';
import ActionButton from '../ActionButton.vue';
import { h } from 'vue';

export default {
	name: 'SiteAnalytics',
	props: ['name'],
	components: {
		BarChart,
		LineChart,
		TabButtons,
		SiteUptime,
		AlertBanner,
		AnalyticsCard,
		DateTimePicker,
	},
	data() {
		return {
			duration: null,
			dateRangeError: null,
			_zoomTimeout: null,
			highlightedCardId: null,
			now: dayjs(),
			defaultDuration: '1h',
			allowTimestampSyncToUrl: true,
			inputStartDate: null,
			logicalStartDate: null,
			inputEndDate: null,
			logicalEndDate: null,
			showAdvancedAnalytics: false,
			localTimezone: dayjs.tz.guess(),
			slowLogsDurationType: 'Denormalized',
			slowLogsFrequencyType: 'Denormalized',
			allowDrillDown: false,
			durationOptions: [
				{ label: 'Duration', value: null, disabled: true },
				/* Using allowed units for value: https://day.js.org/docs/en/manipulate/add#list-of-all-available-units */
				{ label: 'Last 1 hour', value: '1h' },
				{ label: 'Last 6 hours', value: '6h' },
				{ label: 'Last day', value: '24h' },
				{ label: 'Last 3 days', value: '3d' },
				{ label: 'Last 7 days', value: '7d' },
				{ label: 'Last 15 days', value: '15d' },
			],
		};
	},
	mounted() {
		// Initialize date range from URL if present
		const start = dayjs(this.$route.query.start);
		const end = dayjs(this.$route.query.end);
		if (start.isValid && end.isValid && start.isBefore(end)) {
			this.updateStartDate(start);
			this.updateEndDate(end);
		} else {
			this.applyDefaultDateRange();
		}

		// Highlight card if element hash found in URL
		if (typeof this.$route.hash === 'string') {
			const slug = this.$route.hash.replace('#', '');
			this.highlightCard(slug);
		}
	},
	resources: {
		analytics() {
			return {
				url: 'press.api.analytics.get',
				params: {
					name: this.name,
					timezone: this.localTimezone,
					start: this.logicalStartDate,
					end: this.logicalEndDate,
				},
				auto: this.logicalStartDate && this.logicalEndDate,
			};
		},
		advancedAnalytics() {
			return {
				url: 'press.api.analytics.get_advanced_analytics',
				params: {
					name: this.name,
					timezone: this.localTimezone,
					start: this.logicalStartDate,
					end: this.logicalEndDate,
				},
				auto:
					this.showAdvancedAnalytics &&
					this.logicalStartDate &&
					this.logicalEndDate,
			};
		},
		slowLogsCount() {
			return {
				url: 'press.api.analytics.get_slow_logs_by_query',
				params: {
					name: this.name,
					agg_type: 'count',
					timezone: this.localTimezone,
					start: this.logicalStartDate,
					end: this.logicalEndDate,
					normalize: this.slowLogsFrequencyType === 'Normalized',
				},
				auto:
					this.showAdvancedAnalytics &&
					this.logicalStartDate &&
					this.logicalEndDate,
			};
		},
		slowLogsDuration() {
			return {
				url: 'press.api.analytics.get_slow_logs_by_query',
				params: {
					name: this.name,
					agg_type: 'duration',
					timezone: this.localTimezone,
					start: this.logicalStartDate,
					end: this.logicalEndDate,
					normalize: this.slowLogsDurationType === 'Normalized',
				},
				auto:
					this.showAdvancedAnalytics &&
					this.logicalStartDate &&
					this.logicalEndDate,
			};
		},
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
				this.$theme.colors.orange[500],
			];
		},
		usageCounterData() {
			let data = this.$resources.analytics.data?.usage_counter;
			if (!data) return;

			let plan_limit = this.$resources.analytics.data?.plan_limit;

			return {
				datasets: [data.map((d) => [+new Date(d.date), d.value / 1000000])],
				// daily limit marker
				markLine: {
					data: [
						{
							name: 'Daily Compute Limit',
							yAxis: plan_limit,
							label: {
								formatter: '{b}: {c} seconds',
								position: 'middle',
							},
							lineStyle: {
								color: '#f5222d',
							},
						},
					],
					symbol: ['none', 'none'],
				},
			};
		},
		requestCountData() {
			let requestCount = this.$resources.analytics.data?.request_count;
			if (!requestCount) return;

			return {
				datasets: [requestCount.map((d) => [+new Date(d.date), d.value])],
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
		queryReportRunReportsData() {
			let queryReportRunReports =
				this.$resources.advancedAnalytics.data?.query_report_run_reports;
			if (!queryReportRunReports) return;

			return queryReportRunReports;
		},
		runDocMethodMethodnamesData() {
			let runDocMethodMethodnames =
				this.$resources.advancedAnalytics.data?.run_doc_method_methodnames;
			if (!runDocMethodMethodnames) return;

			return runDocMethodMethodnames;
		},
		saveDocsDoctypesData() {
			let saveDocDoctypes =
				this.$resources.advancedAnalytics.data?.save_docs_doctypes;
			if (!saveDocDoctypes) return;

			return saveDocDoctypes;
		},
		saveDocsActionData() {
			let saveDocActions =
				this.$resources.advancedAnalytics.data?.save_docs_actions;
			if (!saveDocActions) return;

			return saveDocActions;
		},
		generateReportReportsData() {
			let generateReportReports =
				this.$resources.advancedAnalytics.data?.generate_report_reports;
			if (!generateReportReports) return;

			return generateReportReports;
		},
		averageRequestDurationByPathData() {
			let averageRequestDurationByPath =
				this.$resources.advancedAnalytics.data
					?.average_request_duration_by_path;
			if (!averageRequestDurationByPath) return;

			return averageRequestDurationByPath;
		},
		requestCountByIPData() {
			let requestCountByIP =
				this.$resources.advancedAnalytics.data?.request_count_by_ip;
			if (!requestCountByIP) return;

			return requestCountByIP;
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
		slowLogsDurationData() {
			const slowLogs = this.$resources.slowLogsDuration.data;
			if (!slowLogs) return;

			return slowLogs;
		},
		slowLogsCountData() {
			const slowLogs = this.$resources.slowLogsCount.data;
			if (!slowLogs) return;

			return slowLogs;
		},
		requestTimeData() {
			let requestCpuTime = this.$resources.analytics.data?.request_cpu_time;
			if (!requestCpuTime) return;

			return {
				datasets: [
					requestCpuTime.map((d) => [+new Date(d.date), d.value / 1000000]),
				],
			};
		},
		jobCountData() {
			let jobCount = this.$resources.advancedAnalytics.data?.job_count;
			if (!jobCount) return;

			return {
				datasets: [jobCount.map((d) => [+new Date(d.date), d.value])],
			};
		},
		jobTimeData() {
			let jobCpuTime = this.$resources.advancedAnalytics.data?.job_cpu_time;
			if (!jobCpuTime) return;

			return {
				datasets: [
					jobCpuTime.map((d) => [+new Date(d.date), d.value / 1000000]),
				],
			};
		},
		shareDashboardActionPrefix() {
			return () => h(ShareIcon, { class: 'w-4 h-4' });
		},
	},
	methods: {
		toggleAdvancedAnalytics() {
			this.showAdvancedAnalytics = !this.showAdvancedAnalytics;
		},
		handleDataZoom(evt) {
			clearTimeout(this._zoomTimeout);

			this._zoomTimeout = setTimeout(() => {
				const { startDate, endDate } = evt;
				this.updateStartDate(startDate);
				this.updateEndDate(endDate);
			}, 500); // debounce
		},
		dateFormatter(dateString) {
			return dayjs(dateString, 'YYYY-MM-DD HH:mm:ss').format(
				'MMM D, YYYY h:mm A',
			);
		},
		resetDateRangeError(msg = null) {
			this.dateRangeError = msg;
		},
		resetDurationField(value = null) {
			this.duration = value;
		},
		applyDefaultDateRange() {
			this.duration = this.defaultDuration;
		},
		syncLogicalDateRange() {
			this.logicalStartDate = this.inputStartDate;
			this.logicalEndDate = this.inputEndDate;
		},
		validateDateRange(start = this.inputStartDate, end = this.inputEndDate) {
			return dayjs(start).isBefore(dayjs(end));
		},
		updateStartDate(newStartDate, resetDuration = true) {
			this.resetDateRangeError();
			if (resetDuration) {
				this.resetDurationField();
			}

			this.inputStartDate = dayjs(newStartDate);

			if (this.allowTimestampSyncToUrl) {
				// Update the query params
				this.$router.push({
					query: {
						...this.$route.query,
						start: this.inputStartDate?.toISOString(),
						end: this.inputEndDate?.toISOString(),
					},
				});
			}

			if (!this.validateDateRange()) {
				this.dateRangeError = 'Invalid date range';
			} else {
				this.syncLogicalDateRange();
			}
		},
		updateEndDate(newEndDate, resetDuration = true) {
			this.resetDateRangeError();
			if (resetDuration) {
				this.resetDurationField();
			}

			this.inputEndDate = dayjs(newEndDate);

			if (this.allowTimestampSyncToUrl) {
				// Update the query params
				this.$router.push({
					query: {
						...this.$route.query,
						start: this.inputStartDate?.toISOString(),
						end: this.inputEndDate?.toISOString(),
					},
				});
			}

			if (!this.validateDateRange()) {
				this.dateRangeError = 'Invalid date range';
			} else {
				this.syncLogicalDateRange();
			}
		},
		highlightCard(slug) {
			if (!slug) return;

			document.getElementById(slug)?.scrollIntoView({
				behavior: 'smooth',
				block: 'center',
			});
		},
		shareDashboard(evt, context = 'card') {
			if (!['card', 'global'].includes(context))
				throw new Error('Invalid share context');

			if (context === 'card') {
				const url = new URL(
					`${window.location.href}?start=${this.inputStartDate}&end=${this.inputEndDate}`,
				);
				url.hash = `#${evt}`;
				navigator.clipboard?.writeText(url.toString());
				toast.success('Card link copied to clipboard!');
			} else if (context === 'global') {
				const url = new URL(
					`${window.location.href}?start=${this.inputStartDate}&end=${this.inputEndDate}`,
				);
				navigator.clipboard?.writeText(url.toString());
				toast.success('Dashboard link copied to clipboard!');
			}
		},
	},
	watch: {
		duration(newValue) {
			if (!newValue) return;
			this.now = dayjs();
			this.updateEndDate(this.now, false);
			const int = parseInt(newValue.slice(0, -1));
			const unit = newValue.slice(-1);
			this.updateStartDate(dayjs(this.inputEndDate).subtract(int, unit), false);
		},
	},
};
</script>
