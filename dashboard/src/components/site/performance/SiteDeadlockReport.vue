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
		PerformanceReport,
	},
	data() {
		return {
			start_datetime: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			stop_datetime: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_log_size: 500,
		};
	},
	computed: {
		deadlockReportOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.deadlock_report',
						makeParams: (params) => {
							// for filterControls to work
							if (params) return params;

							return {
								name: this.name,
								start_datetime: this.start_datetime,
								stop_datetime: this.stop_datetime,
								max_log_size: parseInt(this.max_log_size ?? ''),
							};
						},
						auto: true,
						initialData: [],
						transform: (data) => {
							return data.map((record) => {
								// Handle null values
								// because some records can be empty as well, to keep a blank line after two deadlock records
								record.timestamp = record.timestamp
									? this.$format.date(record.timestamp, 'YYYY-MM-DD HH:mm:ss')
									: '';
								record.transaction_id = record.transaction_id || '';
								record.table = record.table || '';
								record.query = record.query || '';
								return record;
							});
						},
					};
				},
				emptyStateMessage: 'No query deadlock records found',
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: '12rem',
						format: (value) => {
							return this.$format.date(value, 'YYYY-MM-DD HH:mm:ss');
						},
					},
					{
						label: 'Txn ID',
						fieldname: 'transaction_id',
						align: 'left',
						width: '100px',
					},
					{
						label: 'Table',
						fieldname: 'table',
						class: 'text-gray-600',
						align: 'left',
						width: '200px',
					},
					{
						label: 'Query',
						fieldname: 'query',
						class: 'font-mono',
					},
				],
				filterControls: () => {
					return [
						{
							type: 'datetime-local',
							label: 'Start Time',
							fieldname: 'start_datetime',
							default: this.start_datetime,
						},
						{
							type: 'datetime-local',
							label: 'End Time',
							fieldname: 'stop_datetime',
							default: this.stop_datetime,
						},
						{
							label: 'Max Log Lines',
							fieldname: 'max_log_size',
							default: this.max_log_size,
						},
					];
				},
			};
		},
	},
};
</script>
