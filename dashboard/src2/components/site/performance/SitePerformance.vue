<template>
	<!-- <div class="grid grid-cols-1 gap-5 sm:grid-cols-3"> -->
	<!-- <div
		v-if="$route.fullPath.endsWith('/performance')"
		class="mx-auto flex max-w-2xl flex-col gap-3"
	> -->
	<!-- <div
			class="hover:bg-gray-100 sm:rounded-md sm:border sm:border-gray-100 sm:px-2 sm:py-1 sm:shadow"
		>
			<router-link :to="{ name: 'SiteRequestLogs', params: { siteName } }">
				<div class="py-2 text-gray-900 sm:px-2">Request Logs</div>
			</router-link>
		</div> -->
	<!-- <div
			class="hover:bg-gray-100 sm:rounded-md sm:border sm:border-gray-100 sm:px-2 sm:py-1 sm:shadow"
		>
			<router-link :to="{ name: 'Site Performance Binary Logs' }">
				<div class="py-2 text-gray-900 sm:px-2">Mariadb Binary Log Report</div>
			</router-link>
		</div>
		<div
			class="hover:bg-gray-100 sm:rounded-md sm:border sm:border-gray-100 sm:px-2 sm:py-1 sm:shadow"
		>
			<router-link :to="{ name: 'Site Performance Process List' }">
				<div class="py-2 text-gray-900 sm:px-2">Mariadb Process List</div>
			</router-link>
		</div>
		<div
			class="hover:bg-gray-100 sm:rounded-md sm:border sm:border-gray-100 sm:px-2 sm:py-1 sm:shadow"
		>
			<router-link
				:to="{
					name: 'Site Performance Slow Queries'
				}"
			>
				<div class="py-2 text-gray-900 sm:px-2">
					Mariadb Slow Queries Report
				</div>
			</router-link>
		</div> -->
	<!-- <div
			class="hover:bg-gray-100 sm:rounded-md sm:border sm:border-gray-100 sm:px-2 sm:py-1 sm:shadow"
		>
			<router-link :to="{ name: 'SiteDeadlockReport', params: { siteName } }">
				<div class="py-2 text-gray-900 sm:px-2">Deadlock Report</div>
			</router-link>
		</div> -->
	<!-- </div>
	<router-view v-slot="{ Component }">
		<component v-if="site" :is="Component" :site="site"></component>
	</router-view> -->
	<ObjectList class="mt-7" :options="options" />
</template>
<script>
import ObjectList from '../../ObjectList.vue';

export default {
	props: ['site'],
	components: {
		ObjectList
	},
	computed: {
		options() {
			return {
				data: () => [
					{
						title: 'Request Logs',
						description:
							'View detailed logs of all HTTP requests made to the website.',
						route: 'Site Performance Request Logs'
					},
					{
						title: 'Binary Log Report',
						description:
							'Analyze changes made to the database, including data modifications and schema alterations.',
						route: 'Site Performance Binary Logs'
					},
					{
						title: 'Process List Report',
						description:
							'Monitor active database processes, their status, and resource usage.',
						route: 'Site Performance Process List'
					},
					{
						title: 'Slow Queries Report',
						description:
							'Identify and optimize slow-running database queries to improve performance.',
						route: 'Site Performance Slow Queries'
					},
					{
						title: 'Deadlock Report',
						description: ' Shows database conflicts that block transactions.',
						route: 'Site Performance Deadlock Report'
					}
				],
				columns: [
					{
						label: 'Title',
						fieldname: 'title',
						width: 0.3
					},
					{
						label: 'Description',
						fieldname: 'description',
						class: 'text-gray-700'
					},
					{
						label: '',
						fieldname: 'action',
						type: 'Button',
						align: 'right',
						width: 0.1,
						Button: ({ row }) => {
							return {
								label: 'View',
								type: 'primary',
								iconRight: 'arrow-right',
								onClick: () => {
									this.$router.push({
										name: row.route
									});
								}
							};
						}
					}
				]
			};
		}
	}
};
</script>
