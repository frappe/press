<template>
	<PerformanceReport
		title="Request Log Report"
		:site="name"
		:reportOptions="requestLogsOptions"
	/>
</template>

<script>
import dayjs from '../../../utils/dayjs';
import PerformanceReport from './PerformanceReport.vue';

export default {
	name: 'SiteRequestLogs',
	props: ['name'],
	components: {
		PerformanceReport
	},
	data() {
		return {
			date: null,
			start: 0
		};
	},
	computed: {
		requestLogsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.request_logs',
						makeParams: params => {
							// for filterControls to work
							if (params) return params;

							return {
								name: this.name,
								timezone: dayjs.tz.guess(),
								sort: 'CPU Time (Descending)',
								date: this.today,
								start: this.start
							};
						},
						auto: true,
						initialData: [],
						transform: data => {
							return data.map(log => {
								log.time = dayjs(log.timestamp).format('HH:mm:ss z');
								log.method = log.request.method;
								log.path = log.request.path;
								log.status = log.request.status_code;
								log.cpu_time = log.duration / 1000000;
								return log;
							});
						}
					};
				},
				columns: [
					{ label: 'Time', fieldname: 'time', width: 1 },
					{ label: 'Method', fieldname: 'method', width: 0.5 },
					{ label: 'Path', fieldname: 'path', width: 2, class: 'font-mono' },
					{
						label: 'Status Code',
						fieldname: 'status',
						width: 0.5,
						align: 'right'
					},
					{
						label: 'CPU Time (seconds)',
						fieldname: 'cpu_time',
						width: 1,
						class: 'text-gray-600',
						align: 'right',
						format: value => value.toFixed(2)
					}
				],
				filterControls: () => [
					{
						type: 'select',
						label: 'Sort',
						fieldname: 'sort',
						class: !this.$isMobile ? 'w-48' : '',
						options: [
							'Time (Ascending)',
							'Time (Descending)',
							'CPU Time (Descending)'
						],
						default: 'CPU Time (Descending)'
					},
					{
						type: 'date',
						label: 'Date',
						fieldname: 'date',
						class: !this.$isMobile ? 'w-48' : '',
						default: this.today
					}
				]
			};
		},
		today() {
			return dayjs().format('YYYY-MM-DD');
		}
	}
};
</script>
