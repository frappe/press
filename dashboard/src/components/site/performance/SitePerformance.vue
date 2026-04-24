<template>
	<ObjectList class="px-3" :options="options" />
</template>
<script>
import ObjectList from '../../ObjectList.vue';

export default {
	props: ['name'],
	components: {
		ObjectList,
	},
	computed: {
		options() {
			return {
				route(row) {
					return {
						name: row.route,
						params: { name: this.name },
					};
				},
				data: () => [
					{
						title: 'Request Log Report',
						description:
							'View detailed logs of all HTTP requests made to the website.',
						route: 'Site Performance Request Logs',
					},
					{
						title: 'Process List Report',
						description:
							'Monitor active database processes, their status, and resource usage.',
						route: 'Site Performance Process List',
					},
					{
						title: 'Slow Queries Report',
						description:
							'Identify and optimize slow-running database queries to improve performance.',
						route: 'Site Performance Slow Queries',
					},
					{
						title: 'Deadlock Report',
						description: 'Shows database conflicts that block transactions.',
						route: 'Site Performance Deadlock Report',
					},
				],
				columns: [
					{
						label: 'Title',
						fieldname: 'title',
						width: 0.3,
					},
					{
						label: 'Description',
						fieldname: 'description',
						class: 'text-gray-700',
					},
				],
			};
		},
	},
};
</script>
