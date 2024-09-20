<template>
	<PerformanceReport :site="name" :reportOptions="deadlockReportOptions" />
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
			today: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			yesterday: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_lines: 20
		};
	},
	computed: {
		deadlockReportOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.deadlock_report',
						makeParams: params => {
							// need to return params if it exists for filterControls to work
							if (params) return params;

							return {
								site: this.name,
								start: this.yesterday,
								end: this.today,
								max_lines: this.max_lines
							};
						},
						auto: true,
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
				actions: () => {
					return [
						{
							label: 'Back',
							icon: 'arrow-left',
							onClick: () => {
								this.$router.push({ name: 'Site Detail Performance' });
							}
						}
					];
				},
				filterControls: () => {
					return [
						{
							type: 'datetime-local',
							label: 'Start Time',
							fieldname: 'start',
							default: this.yesterday
						},
						{
							type: 'datetime-local',
							label: 'End Time',
							fieldname: 'end',
							default: this.today
						},
						{
							label: 'Max Lines',
							fieldname: 'max_lines',
							default: this.max_lines
						}
					];
				}
			};
		}
	}
};
</script>
