<template>
	<PerformanceReport
		title="Query Deadlocks"
		:site="name"
		:reportOptions="deadlockReportOptions"
	/>
</template>

<script>
import dayjs from '../../../utils/dayjs';
import PerformanceReport from './PerformanceReport.vue';

export default {
	name: 'SiteDeadlockReport',
	props: ['name'],
	components: {
		PerformanceReport
	},
	data() {
		return {
			start_datetime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			stop_datetime: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_log_size: 500
		};
	},
	computed: {
		deadlockReportOptions() {
			return {
				data: () => this.$resources.deadlockReport.data.data,
				emptyStateMessage: 'No query deadlock records found',
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: '12rem',
						format: value => {
							return this.$format.date(value, 'YYYY-MM-DD HH:mm:ss');
						}
					},
					{
						label: 'Txn ID',
						fieldname: 'transaction_id',
						align: 'left',
						width: '100px'
					},
					{
						label: 'Table',
						fieldname: 'table',
						class: 'text-gray-600',
						align: 'left',
						width: '200px'
					},
					{
						label: 'Query',
						fieldname: 'query',
						class: 'font-mono',
						width: '600px'
					}
				],
				actions: () => [
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.deadlockReport.loading,
						onClick: () => this.$resources.deadlockReport.reload()
					}
				],
				filterControls: () => {
					return [
						{
							type: 'datetime-local',
							label: 'Start Time',
							fieldname: 'start_datetime',
							default: this.start_datetime
						},
						{
							type: 'datetime-local',
							label: 'End Time',
							fieldname: 'stop_datetime',
							default: this.stop_datetime
						},
						{
							label: 'Max Log Lines',
							fieldname: 'max_lines',
							default: this.max_log_size
						}
					];
				}
			};
		}
	},
	methods: {
		getDateTimeRange() {
			const formatDateTime = date => {
				return this.$dayjs(date).format('YYYY-MM-DD HH:mm:ss');
			};

			const now = new Date();
			const startDateTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
			const endDateTime = formatDateTime(now);
			const startDateTimeFormatted = formatDateTime(startDateTime);

			return {
				startDateTime: startDateTimeFormatted,
				endDateTime: endDateTime
			};
		}
	},
	resources: {
		deadlockReport() {
			return {
				url: 'press.api.analytics.deadlock_report',
				params: {
					name: this.name,
					start_datetime: this.start_datetime,
					stop_datetime: this.stop_datetime,
					max_log_size: this.max_log_size
				},
				auto: true,
				initialData: { columns: [], data: [] }
			};
		}
	}
};
</script>
