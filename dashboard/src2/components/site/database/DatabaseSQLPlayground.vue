<template>
	<DatabaseToolWrapper title="SQL Playground">
		<div class="mt-2 flex h-full w-full flex-col gap-5" v-if="isSQLEditorReady">
			<div class="w-full">
				<SQLCodeEditor
					v-model="query"
					v-if="sqlSchemaForAutocompletion"
					:schema="sqlSchemaForAutocompletion"
				/>
				<Button
					class="mt-2"
					@click="runSQLQuery"
					:loading="$resources.runSQLQuery.loading"
					iconLeft="play"
					>Run Query</Button
				>
			</div>
			<div
				v-if="
					typeof output === 'string' &&
					output &&
					!$resources.runSQLQuery.loading
				"
				class="rounded border p-4 text-base text-gray-700"
			>
				{{ output }}
			</div>
			<SQLResultTable
				v-if="typeof output === 'object' && !$resources.runSQLQuery.loading"
				:columns="output.columns ?? []"
				:data="output.data ?? []"
			/>
		</div>
		<div
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			v-else
		>
			<Spinner class="w-4" /> Setting Up SQL Playground
		</div>
	</DatabaseToolWrapper>
</template>
<script>
import { toast } from 'vue-sonner';
import SQLResultTable from './SQLResultTable.vue';
import SQLCodeEditor from './SQLCodeEditor.vue';
import DatabaseToolWrapper from './DatabaseToolWrapper.vue';

export default {
	name: 'DatabaseSQLPlayground',
	props: ['name'],
	components: {
		DatabaseToolWrapper,
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
			window.localStorage.getItem(`sql_playground_query_${this.name}`) || '';
	},
	watch: {
		query() {
			window.localStorage.setItem(
				`sql_playground_query_${this.name}`,
				this.query
			);
		}
	},
	resources: {
		runSQLQuery() {
			return {
				url: 'press.api.client.run_doc_method',
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
						dn: this.name,
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
	},
	methods: {
		runSQLQuery() {
			this.$resources.runSQLQuery.submit({
				dt: 'Site',
				dn: this.name,
				method: 'run_sql_query_in_database',
				args: {
					query: this.query,
					commit: this.commit
				}
			});
		}
	}
};
</script>
