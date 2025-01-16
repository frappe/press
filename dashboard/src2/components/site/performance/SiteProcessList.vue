<template>
	<div>
		<PerformanceReport
			title="Process List"
			:site="name"
			:reportOptions="processListOptions"
		/>
		<SiteDatabaseProcess
			v-if="show"
			v-model="show"
			:id="selectedRow?.id ?? ''"
			:query="selectedRow?.query ?? ''"
			:host="selectedRow?.db_user_host ?? ''"
			:user="selectedRow?.db_user ?? ''"
			:state="selectedRow?.state ?? ''"
			:command="selectedRow?.command ?? ''"
			:site="name"
			@process-killed="show = false"
		/>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import PerformanceReport from './PerformanceReport.vue';
import SiteDatabaseProcess from './SiteDatabaseProcess.vue';

export default {
	name: 'SiteMariaDBProcessList',
	props: ['name'],
	components: {
		PerformanceReport,
		SiteDatabaseProcess,
	},
	data() {
		return {
			show: false,
			selectedRow: null,
		};
	},
	computed: {
		processListOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.mariadb_processlist',
						params: {
							site: this.name,
						},
						auto: true,
						initialData: [],
					};
				},
				columns: [
					{
						label: 'ID',
						fieldname: 'id',
						width: '4rem',
					},
					{
						label: 'Time',
						fieldname: 'time',
						width: '6rem',
						align: 'right',
					},
					{
						label: 'Command',
						fieldname: 'command',
						width: '6rem',
					},
					{
						label: 'State',
						fieldname: 'state',
						width: '8rem',
					},
					{
						label: 'Query',
						fieldname: 'query',
						class: 'font-mono',
					},
				],
				onRowClick: (row) => {
					this.selectedRow = row;
					this.show = true;
				},
			};
		},
	},
	methods: {
		processKilledCallback() {
			toast.success('Database Process Killed');
			this.show = false;
		},
	},
};
</script>
