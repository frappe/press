<template>
	<!-- <div class="grid grid-cols-1 gap-5 sm:grid-cols-3"> -->
	<div class="flex flex-col gap-3">
		<div
			class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow hover:bg-gray-100"
		>
			<router-link
				:to="{ name: 'SiteRequestLogs', params: { siteName: site.name } }"
			>
				<div class="py-2 text-gray-900 sm:px-2">Request Logs</div>
			</router-link>
		</div>
		<div
			class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow hover:bg-gray-100"
		>
			<router-link
				:to="{ name: 'SiteBinaryLogs', params: { siteName: site.name } }"
			>
				<div class="py-2 text-gray-900 sm:px-2">Mariadb Binary Log Report</div>
			</router-link>
		</div>
		<div
			class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow hover:bg-gray-100"
		>
			<router-link
				:to="{ name: 'MariaDBProcessList', params: { siteName: site.name } }"
			>
				<div class="py-2 text-gray-900 sm:px-2">Mariadb Process List</div>
			</router-link>
		</div>
		<div
			class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow hover:bg-gray-100"
		>
			<router-link
				:to="{
					name: 'SiteMariaDBSlowQueries',
					params: { siteName: site.name }
				}"
			>
				<div class="py-2 text-gray-900 sm:px-2">
					Mariadb Slow Queries Report
				</div>
			</router-link>
		</div>
		<div
			class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow hover:bg-gray-100"
		>
			<router-link
				:to="{ name: 'SiteDeadlockReport', params: { siteName: site.name } }"
			>
				<div class="py-2 text-gray-900 sm:px-2">Deadlock Report</div>
			</router-link>
		</div>
	</div>
</template>
<script>
import Report from '@/components/Report.vue';

export default {
	name: 'SiteMonitorsList',
	props: ['site'],
	components: {
		Report
	}
};
</script>
