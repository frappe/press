<template>
	<PerformanceReport
		title="Nginx Log Report"
		:site="name"
		:reportOptions="nginxLogsOptions"
	/>
</template>

<script>
import dayjs from '../../../utils/dayjs'
import PerformanceReport from './PerformanceReport.vue'

export default {
	name: 'SiteNginxLogs',
	props: ['name'],
	components: {
		PerformanceReport,
	},
	computed: {
		nginxLogsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.nginx_logs.get',
						makeParams: (params) => {
							// for filterControls to work
							if (params) return params

							return {
								name: this.name,
								timezone: dayjs.tz.guess(),
								date: this.today,
								status: 'All',
							}
						},
						auto: true,
						initialData: [],
						transform: (data) => {
							return data.map((log) => {
								log.time = dayjs(log.timestamp).format('HH:mm:ss z')
								return log
							})
						},
					}
				},
				columns: [
					{ label: 'Time', fieldname: 'time', width: 1 },
					{ label: 'Method', fieldname: 'method', width: 0.5 },
					{ label: 'Path', fieldname: 'path', width: 2, class: 'font-mono' },
					{
						label: 'Status Code',
						fieldname: 'status',
						width: 0.5,
						align: 'right',
					},
					{
						label: 'Duration (seconds)',
						fieldname: 'duration',
						width: 0.75,
						class: 'text-ink-gray-6',
						align: 'right',
					},
					{ label: 'IP', fieldname: 'ip', width: 1, class: 'font-mono' },
				],
				filterControls: () => [
					{
						type: 'select',
						label: 'Status',
						fieldname: 'status',
						class: !this.$isMobile ? 'w-48' : '',
						options: ['All', 'Errors (4xx, 5xx)', 'Server Errors (5xx)'],
						default: 'All',
					},
					{
						type: 'date',
						label: 'Date',
						fieldname: 'date',
						class: !this.$isMobile ? 'w-48' : '',
						default: this.today,
					},
				],
			}
		},
		today() {
			return dayjs().format('YYYY-MM-DD')
		},
	},
}
</script>
