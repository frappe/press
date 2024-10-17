<template>
	<div class="mt-2 flex h-full w-full flex-col gap-5">
		<div class="w-full">
			<Textarea
				variant="outline"
				size="sm"
				placeholder="Write your SQL query here"
				label="SQL Query"
				class="w-full"
				v-model="query"
				:rows="10"
			></Textarea>
			<Button
				class="mt-2"
				@click="$resources.runSQLQuery.submit"
				:loading="$resources.runSQLQuery.loading"
				>Run Query</Button
			>
		</div>
		<div
			v-if="typeof output === 'string' && output"
			class="rounded border p-4 text-base text-gray-700"
		>
			{{ output }}
		</div>
		<SQLResultTable
			v-if="typeof output === 'object'"
			:columns="output.columns ?? []"
			:data="output.data ?? []"
		/>
	</div>
</template>
<script>
import { Textarea, Button } from 'frappe-ui';
import { toast } from 'vue-sonner';
import SQLResultTable from './SQLResultTable.vue';

export default {
	name: 'DatabaseSQLPlayground',
	inject: ['site'],
	components: {
		SQLResultTable
	},
	data() {
		return {
			query: '',
			commit: false,
			execution_successful: null,
			output: ''
		};
	},
	mounted() {
		this.query =
			window.localStorage.getItem(`sql_playground_query_${this.site}`) || '';
	},
	watch: {
		query() {
			window.localStorage.setItem(
				`sql_playground_query_${this.site}`,
				this.query
			);
		}
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
					this.output = data?.message?.output ?? {};
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
