<template>
	<div class="mt-2 flex h-full w-full flex-col gap-5" v-if="isSQLEditorReady">
		<div class="w-full">
			<SQLCodeEditor
				v-model="query"
				v-if="sqlSchemaForAutocompletion"
				:schema="sqlSchemaForAutocompletion"
			/>
			<Button
				class="mt-2"
				@click="$resources.runSQLQuery.submit"
				:loading="$resources.runSQLQuery.loading"
				iconLeft="play"
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
	<div
		class="flex h-full w-full justify-center items-center min-h-[80vh] text-gray-700 gap-2"
		v-else
	>
		<Spinner class="w-4" /> Setting Up SQL Playground
	</div>
</template>
<script>
import { Textarea, Button, Spinner } from 'frappe-ui';
import { toast } from 'vue-sonner';
import SQLResultTable from './SQLResultTable.vue';
import SQLCodeEditor from './SQLCodeEditor.vue';

export default {
	name: 'DatabaseSQLPlayground',
	inject: ['site'],
	components: {
		SQLResultTable,
		SQLCodeEditor
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
		},
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'fetch_database_table_schemas'
					};
				},
				initialData: {},
				auto: true
			};
		}
	},
	computed: {
		sqlSchemaForAutocompletion() {
			const tableSchemas = this.$resources.tableSchemas?.data?.message ?? {};
			if (!tableSchemas || !Object.keys(tableSchemas).length) return null;
			let childrenSchemas = {};
			for (const tableName in tableSchemas) {
				childrenSchemas[tableName] = {
					self: { label: tableName, type: 'table' },
					children: tableSchemas[tableName].map(x => ({
						label: x.column,
						type: 'column',
						detail: x.data_type
					}))
				};
			}
			return {
				self: { label: 'SQL Schema', type: 'schema' },
				children: childrenSchemas
			};
		},
		isSQLEditorReady() {
			if (this.$resources.tableSchemas.loading) return false;
			if (!this.sqlSchemaForAutocompletion) return false;
			return true;
		}
	}
};
</script>
