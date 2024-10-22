<template>
	<div v-if="typeof result.output === 'object' && result.output">
		<SQLResultTable
			:columns="result.output?.columns ?? []"
			:data="result.output?.data ?? []"
		/>
		<div class="output-container mt-2">
			SQL Query -
			<pre class="mt-2 text-sm">{{ result.query }}</pre>
		</div>
	</div>

	<div v-else class="output-container">
		<pre class="mb-4 text-sm">{{ result.query }}</pre>
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
	}
};
</script>
