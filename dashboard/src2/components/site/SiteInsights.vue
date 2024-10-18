<template>
	<div class="flex space-x-6 divide-x">
		<div
			class="h-min w-60 divide-y overflow-hidden rounded-sm border border-gray-200"
		>
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value }"
					v
					class="flex cursor-pointer text-base text-gray-600 hover:bg-gray-50"
					:class="{
						' text-gray-800': currentTab === tab.value,
						'text-gray-600': currentTab !== tab.value
					}"
					@click="currentTab = tab.value"
				>
					<div
						v-if="currentTab === tab.value"
						class="inline w-0.5 bg-gray-800"
					></div>
					<div
						class="px-4 py-2"
						:class="{
							'-ml-0.5': currentTab === tab.value
						}"
					>
						{{ tab.label }}
					</div>
				</router-link>
			</template>
		</div>
		<div class="min-h-screen w-full">
			<router-view />
		</div>
	</div>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import dayjs from '../../utils/dayjs';
import { duration } from '../../utils/format';
import LineChart from '@/components/charts/LineChart.vue';
import SiteUptime from './SiteUptime.vue';
import AnalyticsCard from './AnalyticsCard.vue';
import SitePerformance from './performance/SitePerformance.vue';
import ObjectList from '../ObjectList.vue';

export default {
	name: 'SiteInsights',
	props: ['site'],
	components: {
		LineChart,
		ObjectList,
		SiteUptime,
		AnalyticsCard,
		SitePerformance
	},
	data() {
		return {
			tabs: [
				{
					label: 'Analytics',
					value: 'Site Analytics'
				},
				{
					label: 'Performance Reports',
					value: 'Site Performance Reports'
				},
				{
					label: 'Logs',
					value: 'Site Logs'
				},
				{
					label: 'Jobs',
					value: 'Site Jobs'
				}
			],
			currentTab: this.$route.name
		};
	},
	mounted() {
		if (this.$route.name === 'Site Insights') {
			this.$router.push({ name: 'Site Analytics' });
		}
	},
	resources: {
		requestCounter() {
			let localTimezone = dayjs.tz.guess();
			return {
				url: 'press.api.analytics.daily_usage',
				params: { name: this.site, timezone: localTimezone },
				auto: true
			};
		},
		uptime() {
			let localTimezone = dayjs.tz.guess();
			return {
				url: 'press.api.analytics.get_uptime',
				params: {
					site: this.site,
					timezone: localTimezone,
					timespan: 24 * 60 * 60,
					timegrain: 30 * 60
				},
				transform(data) {
					const paddedData = data.concat(Array(60).fill({}));
					return paddedData.slice(0, 60);
				},
				auto: true
			};
		},
		siteLogs() {
			return {
				url: 'press.api.site.logs',
				params: {
					name: this.site
				},
				auto: true,
				cache: ['ObjectList', 'press.api.site.logs', this.site],
				transform(data) {
					return data.splice(0, 5);
				},
				initialData: []
			};
		},
		siteJobs() {
			return {
				type: 'list',
				doctype: 'Agent Job',
				filters: {
					site: this.site
				},
				orderBy: 'creation desc',
				fields: [
					'end',
					'job_id',
					'name',
					'status',
					'creation',
					'job_type',
					'duration',
					'owner'
				],
				auto: true,
				cache: ['ObjectList', 'Agent Job', this.site],
				transform(data) {
					return data.splice(0, 5);
				},
				initialData: []
			};
		}
	},
	computed: {
		dailyUsageData() {
			let dailyUsageData = this.$resources.requestCounter.data?.data;
			if (!dailyUsageData) return;
			let plan_limit = this.$resources.requestCounter.data.plan_limit;

			return {
				datasets: [
					dailyUsageData.map(d => [+new Date(d.date), d.value / 1000000])
				],
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
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		logsOptions() {
			return {
				data: () => this.$resources.siteLogs.data,
				route(row) {
					return {
						name: 'Site Log',
						params: { logName: row.name }
					};
				},
				emptyStateMessage: 'No logs found',
				columns: [
					{
						label: 'Name',
						fieldname: 'name'
					},
					{
						label: 'Size',
						fieldname: 'size',
						class: 'text-gray-600',
						format(value) {
							return `${value} kB`;
						}
					},
					{
						label: 'Created On',
						fieldname: 'created',
						format(value) {
							return value ? date(value, 'lll') : '';
						}
					}
				]
			};
		},
		jobsOptions() {
			return {
				data: () => this.$resources.siteJobs?.data || [],
				route(row) {
					return {
						name: 'Site Job',
						params: { id: row.name }
					};
				},
				emptyStateMessage: 'No jobs found',
				columns: [
					{
						label: 'Job Type',
						fieldname: 'job_type',
						class: 'font-medium'
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						width: 0.5
					},
					{
						label: 'Duration',
						fieldname: 'duration',
						width: 0.35,
						format(value, row) {
							if (row.job_id === 0 || !row.end) return;
							return duration(value);
						}
					},
					{
						label: 'Created By',
						fieldname: 'owner'
					},
					{
						label: '',
						fieldname: 'creation',
						type: 'Timestamp',
						width: 0.5,
						align: 'right'
					}
				]
			};
		},
		performanceReportOptions() {
			return {
				data: () => [
					{
						title: 'Request Logs',
						description:
							'View detailed logs of all HTTP requests made to the website.',
						route: 'Site Performance Request Logs'
					},
					{
						title: 'Binary Log Report',
						description:
							'Analyze changes made to the database, including data modifications and schema alterations.',
						route: 'Site Performance Binary Logs'
					},
					{
						title: 'Process List Report',
						description:
							'Monitor active database processes, their status, and resource usage.',
						route: 'Site Performance Process List'
					},
					{
						title: 'Slow Queries Report',
						description:
							'Identify and optimize slow-running database queries to improve performance.',
						route: 'Site Performance Slow Queries'
					}
					// {
					// 	title: 'Deadlock Report',
					// 	description: 'Shows database conflicts that block transactions.',
					// 	route: 'Site Performance Deadlock Report'
					// }
				],
				columns: [
					{
						label: 'Title',
						fieldname: 'title',
						width: 0.3
					},
					{
						label: 'Description',
						fieldname: 'description',
						class: 'text-gray-700'
					},
					{
						label: '',
						fieldname: 'action',
						type: 'Button',
						align: 'right',
						width: 0.1,
						Button: ({ row }) => {
							return {
								label: 'View',
								type: 'primary',
								iconRight: 'arrow-right',
								onClick: () => {
									this.$router.push({
										name: row.route
									});
								}
							};
						}
					}
				]
			};
		}
	}
};
</script>
