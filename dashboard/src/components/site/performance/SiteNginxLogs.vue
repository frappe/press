<template>
	<PerformanceReport
		title="Nginx Log Report"
		:site="name"
		:reportOptions="nginxLogsOptions"
	>
		<div class="mb-4 rounded border">
			<div class="flex items-center justify-between px-3 pt-2">
				<span class="text-sm text-ink-gray-6">
					Requests from {{ formatTime(start) }} to {{ formatTime(end) }}. Drag
					on the chart to zoom in.
				</span>
				<Button v-if="zoomed" label="Reset zoom" @click="setDay(date)" />
			</div>
			<BarChart
				:key="histogram"
				:data="histogram"
				unit="requests"
				:chartTheme="statusColors"
				:loading="$resources.logs.loading"
				:showCard="false"
				class="h-60 p-2"
				@datazoom="zoom"
			/>
		</div>
	</PerformanceReport>
</template>

<script>
import dayjs from '../../../utils/dayjs'
import { theme } from '../../../utils/theme'
import BarChart from '../../charts/BarChart.vue'
import PerformanceReport from './PerformanceReport.vue'

const emptyHistogram = { labels: [], datasets: [] }

export default {
	name: 'SiteNginxLogs',
	props: ['name'],
	components: {
		BarChart,
		PerformanceReport,
	},
	data() {
		const today = dayjs().format('YYYY-MM-DD')
		return {
			date: today,
			status: 'All',
			start: dayjs(today).startOf('day'),
			end: dayjs(today).endOf('day'),
			zoomed: false,
			statusColors: [
				theme.colors.green[500],
				theme.colors.yellow[500],
				theme.colors.red[500],
			],
		}
	},
	resources: {
		logs() {
			return {
				url: 'press.api.nginx_logs.get',
				params: {
					name: this.name,
					timezone: dayjs.tz.guess(),
					start: this.start.toISOString(),
					end: this.end.toISOString(),
					status: this.status,
				},
				auto: true,
				initialData: { rows: [], histogram: emptyHistogram },
			}
		},
	},
	computed: {
		histogram() {
			return this.$resources.logs.data?.histogram || emptyHistogram
		},
		nginxLogsOptions() {
			return {
				data: () =>
					(this.$resources.logs.data?.rows || []).map((log) => ({
						...log,
						time: dayjs(log.timestamp).format('HH:mm:ss z'),
					})),
				isLoading: () => this.$resources.logs.loading,
				updateFilters: (filters) => {
					if ('status' in filters) this.status = filters.status
					if ('date' in filters) this.setDay(filters.date)
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
						default: this.date,
					},
				],
			}
		},
	},
	methods: {
		setDay(date) {
			this.date = date
			this.start = dayjs(date).startOf('day')
			this.end = dayjs(date).endOf('day')
			this.zoomed = false
		},
		zoom({ startDate, endDate }) {
			// The chart fires several events during one drag
			clearTimeout(this._zoomTimeout)
			this._zoomTimeout = setTimeout(() => {
				// A label is the start of its bucket, so add one bucket to the end
				const [first, second] = this.histogram.labels
				const bucketWidth = second ? dayjs(second).diff(dayjs(first)) : 0
				this.start = dayjs(startDate)
				this.end = dayjs(endDate).add(bucketWidth, 'millisecond')
				this.zoomed = true
			}, 500)
		},
		formatTime(time) {
			return time.format('D MMM HH:mm:ss')
		},
	},
}
</script>
