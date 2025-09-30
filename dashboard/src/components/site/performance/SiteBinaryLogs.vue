<template>
	<PerformanceReport
		title="Binary Logs"
		:site="name"
		:reportOptions="binaryLogsOptions"
	/>
</template>

<script>
import dayjs from '../../../utils/dayjs';
import { DashboardError } from '../../../utils/error';
import PerformanceReport from './PerformanceReport.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteBinaryLogs',
	props: ['name'],
	components: { PerformanceReport },
	data() {
		return {
			start_time: dayjs().subtract(2, 'hour').format('YYYY-MM-DD HH:mm:ss'),
			end_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			pattern: '.*',
			max_lines: 50,
		};
	},
	resources: {
		binaryLogs() {
			return {
				url: 'press.api.analytics.binary_logs',
				makeParams: (params) => {
					if (params) return params;

					return {
						name: this.name,
						start_time: this.start_time,
						end_time: this.end_time,
						pattern: this.pattern,
						max_lines: this.max_lines,
					};
				},
				validate() {
					if (this.max_lines < 1 || this.max_lines > 500) {
						toast.error('Max lines should be between 1 and 500');
						throw new DashboardError('Max lines should be between 1 and 500');
					}
					// check between start_time and end_time is less than 2 hours
					const start = dayjs(this.start_time);
					const end = dayjs(this.end_time);
					if (end.diff(start, 'hour') > 2) {
						toast.error('Time range should be less than 2 hours');
						throw new DashboardError('Time range should be less than 2 hours');
					}
					// start_time should be less than end_time
					if (start.isAfter(end)) {
						toast.error('Start time should be less than end time');
						throw new DashboardError('Start time should be less than end time');
					}
				},
				onError(error) {
					console.error(error.message);
				},
				auto: false,
				pageLength: 10,
				keepData: true,
				initialData: [],
			};
		},
	},
	computed: {
		binaryLogsOptions() {
			return {
				data: () => this.$resources.binaryLogs.data,
				updateFilters: (params) => {
					if (!params) return;
					for (const [key, value] of Object.entries(params)) {
						if (key === 'start_time') this.start_time = value;
						if (key === 'end_time') this.end_time = value;
						if (key === 'pattern') this.pattern = value;
						if (key === 'max_lines') this.max_lines = value;
					}
				},
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: '12rem',
						format: (value) => {
							return this.$format.date(value, 'YYYY-MM-DD HH:mm:ss');
						},
					},
					{ label: 'Query', fieldname: 'query', class: 'font-mono' },
				],
				filterControls: () => {
					return [
						{
							type: 'datetime',
							label: 'Start Time',
							fieldname: 'start_time',
							default: this.start_time,
						},
						{
							type: 'datetime',
							label: 'End Time',
							fieldname: 'end_time',
							default: this.end_time,
						},
						{
							label: 'Pattern',
							fieldname: 'pattern',
							default: this.pattern,
						},
						{
							label: 'Max Lines',
							fieldname: 'max_lines',
							default: this.max_lines,
						},
					];
				},
				actions: () => [
					{
						label: 'View Logs',
						variant: 'solid',
						loading: this.$resources.binaryLogs.loading,
						loadingText: 'Loading',
						onClick: () => this.$resources.binaryLogs.reload(),
					},
				],
			};
		},
	},
};
</script>
