<template>
	<PerformanceReport
		title="Process List"
		:site="name"
		:reportOptions="processListOptions"
	/>
</template>

<script>
import PerformanceReport from './PerformanceReport.vue';

export default {
	name: 'SiteMariaDBProcessList',
	props: ['name'],
	components: {
		PerformanceReport
	},
	computed: {
		processListOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.mariadb_processlist',
						params: {
							site: this.name
						},
						auto: true,
						initialData: []
					};
				},
				columns: [
					{
						label: 'ID',
						fieldname: 'Id',
						width: '4rem'
					},
					{
						label: 'Time',
						fieldname: 'Time',
						width: '6rem',
						align: 'right'
					},
					{
						label: 'Command',
						fieldname: 'Command',
						width: '6rem'
					},
					{
						label: 'State',
						fieldname: 'State',
						width: '8rem'
					},
					{
						label: 'Query',
						fieldname: 'Info',
						class: 'font-mono'
					}
				]
			};
		}
	}
};
</script>
