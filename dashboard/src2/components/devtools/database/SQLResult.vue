<template>
	<div v-if="typeof result.output === 'object' && result.output">
		<SQLResultTable
			:columns="result.output?.columns ?? []"
			:data="result.output?.data ?? []"
		/>
		<div class="output-container mt-2 !p-2">
			<Button
				:iconLeft="isSQLQueryVisible ? 'chevron-down' : 'chevron-right'"
				variant="ghost"
				@click="toggleSQLQuerySection"
				>View SQL Query</Button
			>
			<pre class="mt-4 text-sm leading-normal" v-if="isSQLQueryVisible">{{
				result.query
			}}</pre>
		</div>
	</div>

	<div v-else class="output-container">
		<pre class="mb-4 text-sm leading-normal">{{ result.query }}</pre>
		{{ result.row_count }} rows affected<br /><br />
		Query executed successfully
	</div>
</template>
<style scoped>
.output-container {
	@apply rounded border p-4 text-base text-gray-700;
}
</style>
<script>
import SQLResultTable from './SQLResultTable.vue';
export default {
	name: 'SQLResult',
	props: ['result'],
	components: {
		SQLResultTable
	},
	data() {
		return {
			isSQLQueryVisible: false
		};
	},
	methods: {
		toggleSQLQuerySection() {
			this.isSQLQueryVisible = !this.isSQLQueryVisible;
		}
	}
};
</script>
