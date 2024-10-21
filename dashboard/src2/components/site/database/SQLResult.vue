<template>
	<SQLResultTable
		v-if="typeof result.output === 'object' && result.output"
		:columns="result.output?.columns ?? []"
		:data="result.output?.data ?? []"
	/>
	<div v-else class="output-container">
		<pre class="mb-4 text-sm">{{ result.query }}</pre>
		{{ result.row_count }} rows affected<br /><br />
		Query executed successfully
	</div>
</template>
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
