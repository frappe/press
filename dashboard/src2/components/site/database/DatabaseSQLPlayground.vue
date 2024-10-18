<template>
	<DatabaseToolWrapper title="SQL Playground">
		<template #actions v-if="isSQLEditorReady">
			<FormControl
				class="w-min-[200px] cursor-pointer"
				type="select"
				:options="[
					{
						label: 'Read Only&nbsp;&nbsp;&nbsp;&nbsp;',
						value: 'read-only'
					},
					{
						label: 'Read Write&nbsp;&nbsp;&nbsp;&nbsp;',
						value: 'read-write'
					}
				]"
				size="sm"
				variant="outline"
				v-model="mode"
			/>
		</template>
		<template #default>
			<div class="mt-2 flex flex-col" v-if="isSQLEditorReady">
				<div class="overflow-hidden rounded border">
					<SQLCodeEditor
						v-model="query"
						v-if="sqlSchemaForAutocompletion"
						:schema="sqlSchemaForAutocompletion"
					/>
				</div>
				<div class="mt-2 flex flex-row items-center justify-between">
					<div class="flex gap-2">
						<Button iconLeft="table" @click="toggleTableSchemasDialog"
							>Tables</Button
						>
						<Button iconLeft="file-text" @click="toggleLogsDialog">Logs</Button>
					</div>

					<Button
						@click="() => runSQLQuery()"
						:loading="$resources.runSQLQuery.loading"
						iconLeft="play"
						variant="solid"
						>Run Query</Button
					>
				</div>
				<div class="mt-4">
					<div
						v-if="
							typeof output === 'string' &&
							output &&
							!$resources.runSQLQuery.loading
						"
						class="rounded border p-4 text-base text-gray-700"
					>
						{{ prettifiedOutput }}<br /><br />
						{{
							execution_successful
								? 'Query executed successfully'
								: 'Query execution failed'
						}}
					</div>
					<SQLResultTable
						v-if="
							output &&
							typeof output === 'object' &&
							!$resources.runSQLQuery.loading
						"
						:columns="output.columns ?? []"
						:data="output.data ?? []"
					/>
					<div
						v-if="output === null && !$resources.runSQLQuery.loading"
						class="rounded border p-4 text-base text-gray-700"
					>
						No output received<br /><br />
						{{
							execution_successful
								? 'Query executed successfully'
								: 'Query execution failed'
						}}
					</div>
				</div>
			</div>
			<div
				class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
				v-else
			>
				<Spinner class="w-4" /> Setting Up SQL Playground
			</div>
			<DatabaseSQLPlaygroundLog
				:site="this.name"
				v-model="showLogs"
				@rerunQuery="rerunQuery"
			/>
			<DatabaseTableSchemaDialog
				:site="this.name"
				v-model="showTableSchemasDialog"
				@runSQLQuery="runSQLQueryForViewingTable"
			/>
		</template>
	</DatabaseToolWrapper>
</template>
<script>
import { toast } from 'vue-sonner';
import SQLResultTable from './SQLResultTable.vue';
import SQLCodeEditor from './SQLCodeEditor.vue';
import DatabaseToolWrapper from './DatabaseToolWrapper.vue';
import { confirmDialog } from '../../../utils/components';
import DatabaseSQLPlaygroundLog from './DatabaseSQLPlaygroundLog.vue';
import DatabaseTableSchemaDialog from './DatabaseTableSchemaDialog.vue';

export default {
	name: 'DatabaseSQLPlayground',
	props: ['name'],
	components: {
		DatabaseToolWrapper,
		SQLResultTable,
		SQLCodeEditor,
		DatabaseSQLPlaygroundLog,
		DatabaseTableSchemaDialog
	},
	data() {
		return {
			query: '',
			commit: false,
			execution_successful: null,
			output: '',
			mode: 'read-only',
			showLogs: false,
			showTableSchemasDialog: false
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
					this.output = data?.message?.output;
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
		},
		prettifiedOutput() {
			if (typeof this.output !== 'string') return null;
			if (this.execution_successful) return this.output;
			// if error message in (state, message) format, try to parse it
			const regex = /\((\d+),\s*['"](.*?)['"]\)/;
			const match = this.output.match(regex);

			if (match) {
				const statusCode = match[1];
				const errorMessage = match[2];
				return `#${statusCode} - ${errorMessage}`;
			} else {
				return this.output;
			}
		}
	},
	methods: {
		runSQLQuery(ignore_validation = false) {
			if (!this.query) return;
			if (this.mode === 'read-only' || ignore_validation) {
				this.$resources.runSQLQuery.submit({
					dt: 'Site',
					dn: this.name,
					method: 'run_sql_query_in_database',
					args: {
						query: this.query,
						commit: this.mode === 'read-write'
					}
				});
				return;
			}

			confirmDialog({
				title: 'Run SQL Query',
				message: `
You are currently using <strong>Read-Write</strong> mode. All the changes by your SQL Query will be committed to the database.
<br><br>
Are you sure you want to run the query?`,
				primaryAction: {
					label: 'Run Query',
					variant: 'solid',
					onClick: ({ hide }) => {
						this.runSQLQuery(true);
						hide();
					}
				}
			});
		},
		toggleLogsDialog() {
			this.showLogs = !this.showLogs;
		},
		toggleTableSchemasDialog() {
			this.showTableSchemasDialog = !this.showTableSchemasDialog;
		},
		rerunQuery(query) {
			this.query = query;
			this.showLogs = false;
		},
		runSQLQueryForViewingTable(query) {
			// set read-only mode
			this.mode = 'read-only';
			this.showTableSchemasDialog = false;
			this.query = query;
			this.runSQLQuery();
		}
	}
};
</script>
