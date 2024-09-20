<template>
	<PerformanceReport
		title="Binary Logs"
		:site="name"
		:reportOptions="binaryLogsOptions"
	/>
</template>

<script>
import dayjs from '../../../utils/dayjs';
import PerformanceReport from './PerformanceReport.vue';

export default {
	name: 'SiteBinaryLogs',
	props: ['name'],
	components: { PerformanceReport },
	data() {
		return {
			today: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			yesterday: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_lines: 4000
		};
	},
	computed: {
		binaryLogsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.binary_logs',
						makeParams: params => {
							if (params) return params;

							return {
								name: this.name,
								start_time: this.yesterday,
								end_time: this.today,
								pattern: '.*',
								max_lines: this.max_lines
							};
						},
						auto: true,
						pageLength: 10,
						keepData: true,
						initialData: []
					};
				},
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: '12rem',
						format: value => {
							return this.$format.date(value, 'YYYY-MM-DD HH:mm:ss');
						}
					},
					{ label: 'Query', fieldname: 'query', class: 'font-mono' }
				],
				filterControls: () => {
					return [
						{
							type: 'datetime',
							label: 'Start Time',
							fieldname: 'start_time',
							default: this.yesterday
						},
						{
							type: 'datetime',
							label: 'End Time',
							fieldname: 'end_time',
							default: this.today
						},
						{
							label: 'Pattern',
							fieldname: 'pattern',
							default: '.*'
						},
						{
							label: 'Max Lines',
							fieldname: 'max_lines',
							default: 4000
						}
					];
				}
			};
		}
	}
};
</script>
