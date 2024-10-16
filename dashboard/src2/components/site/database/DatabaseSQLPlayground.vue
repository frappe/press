<template>
	<div class="mt-2 flex h-full w-full flex-row gap-10">
		<div class="w-1/2">
			<Textarea
				variant="outline"
				size="sm"
				placeholder="Write your SQL query here"
				label="SQL Query"
				class="w-full"
				v-model="query"
				:rows="40"
			></Textarea>
			<Button
				class="mt-2"
				@click="$resources.runSQLQuery.submit"
				:loading="$resources.runSQLQuery.loading"
				>Run Query</Button
			>
		</div>
		<div class="w-1/2 text-xs">
			<p>{{ output }}</p>
		</div>
	</div>
</template>
<script>
import { Textarea, Button } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'DatabaseSQLPlayground',
	inject: ['site'],
	data() {
		return {
			query: '',
			commit: false,
			execution_successful: null,
			output: ''
		};
	},
	resources: {
		runSQLQuery() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'run_sql_query_in_database',
						args: {
							query: this.query,
							commit: this.commit
						}
					};
				},
				onSuccess: data => {
					this.output = data?.message?.output ?? 'No output';
					this.execution_successful = data?.message?.success || false;
				},
				onError: e => {
					toast.error(
						e.messages?.length
							? e.messages.join('\n')
							: e.message || 'Failed to run SQL query'
					);
				},
				auto: false
			};
		}
	}
};
</script>
