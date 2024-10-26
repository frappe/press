<template>
	<ObjectList class="px-5 pt-5" :options="options" />
</template>
<script>
import ObjectList from '../../ObjectList.vue';

export default {
	props: ['name'],
	components: {
		ObjectList
	},
	computed: {
		options() {
			return {
				data: () => [
					{
						title: 'Request Log Report',
						description:
							'View detailed logs of all HTTP requests made to the website.',
						route: 'Site Performance Request Logs'
					},
					{
						title: 'Binary Log Report',
						description:
							'Analyze changes made to the database, including data changes and schema alterations.',
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
					}
					// {
					// 	title: 'Deadlock Report',
					// 	description: 'Shows database conflicts that block transactions.',
					// 	route: 'Site Performance Deadlock Report'
					// }
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
									this.$router.push({ name: row.route });
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
