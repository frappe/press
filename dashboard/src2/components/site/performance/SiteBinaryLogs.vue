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
			start_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			end_time: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_lines: 500
		};
	},
	resources: {
		binaryLogs() {
			return {
				url: 'press.api.analytics.binary_logs',
				makeParams: params => {
					if (params) return params;

					return {
						name: this.name,
						start_time: this.end_time,
						end_time: this.start_time,
						pattern: '.*',
						max_lines: this.max_lines
					};
				},
				auto: false,
				pageLength: 10,
				keepData: true,
				initialData: []
			};
		}
	},
	computed: {
		binaryLogsOptions() {
			return {
				data: () => this.$resources.binaryLogs.data,
				updateFilters: params => {
					if (!params) return;
					for (const [key, value] of Object.entries(params)) {
						this[key] = value;
					}
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
							default: this.start_time
						},
						{
							type: 'datetime',
							label: 'End Time',
							fieldname: 'end_time',
							default: this.end_time
						},
						{
							label: 'Pattern',
							fieldname: 'pattern',
							default: '.*'
						},
						{
							label: 'Max Lines',
							fieldname: 'max_lines',
							default: 500
						}
					];
				},
				actions: () => [
					{
						label: 'View Logs',
						variant: 'solid',
						loading: true || this.$resources.binaryLogs.loading,
						loadingText: 'Loading',
						onClick: () => this.$resources.binaryLogs.reload()
					}
				]
			};
		}
	}
};
</script>
