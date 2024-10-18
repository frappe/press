<template>
	<div class="mx-auto max-w-3xl space-y-4">
		<div class="divide-y rounded border border-gray-200 p-5">
			<div class="pb-3 text-lg font-semibold">Database Toolkit</div>
			<DatabaseToolkitButton
				v-for="button in buttonDefinitions"
				:key="button.action"
				:details="button"
				:onClick="onClickToolButton"
			/>
		</div>
	</div>
</template>
<script>
import DatabaseToolkitButton from './DatabaseToolkitButton.vue';

export default {
	name: 'DatabaseToolkit',
	props: ['site'],
	components: {
		DatabaseToolkitButton
	},
	data() {
		return {
			buttonDefinitions: [
				{
					label: 'Browse Schema',
					description: 'Browse your database schema',
					buttonLabel: 'View',
					route: 'Database Toolkit Browse Schema'
				},
				{
					label: 'SQL Playground',
					description: 'Run SQL queries against your database',
					buttonLabel: 'Start',
					route: 'Database Toolkit SQL Playground'
				}
			]
		};
	},
	methods: {
		onClickToolButton(details) {
			this.$router.push({ name: details.route });
		}
	}
};
</script>
