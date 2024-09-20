<template>
	<Report
		title="Process List"
		:site="name"
		:reportOptions="processListOptions"
	/>
</template>

<script>
import Report from './Report.vue';

export default {
	name: 'SiteMariaDBProcessList',
	props: ['name'],
	components: {
		Report
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
						width: '6rem'
					},
					{
						label: 'User',
						fieldname: 'User',
						width: '15rem'
					},
					{
						label: 'Time',
						fieldname: 'Time',
						width: '6rem'
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
