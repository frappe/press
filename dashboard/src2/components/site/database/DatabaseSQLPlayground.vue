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
				<div
					class="mt-4"
					v-if="!$resources.runSQLQuery.loading && (data || errorMessage)"
				>
					<div v-if="errorMessage" class="output-container">
						{{ prettifySQLError(errorMessage) }}<br /><br />
						Query execution failed
					</div>
					<div v-else-if="data.length == 0" class="output-container">
						No output received
					</div>
					<div v-else-if="data.length == 1">
						<SQLResult :result="data[0]" />
					</div>
					<div v-else>
						<FTabs :tabs="sqlResultTabs" v-model="tabIndex">
							<template #default="{ tab }">
								<div class="pt-5">
									<SQLResult :result="tab" />
								</div>
							</template>
						</FTabs>
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
<style scoped>
.output-container {
	@apply rounded border p-4 text-base text-gray-700;
}
</style>
<script>
import { toast } from 'vue-sonner';
import { Tabs } from 'frappe-ui';
import SQLResultTable from './SQLResultTable.vue';
import SQLCodeEditor from './SQLCodeEditor.vue';
import DatabaseToolWrapper from './DatabaseToolWrapper.vue';
import { confirmDialog } from '../../../utils/components';
import DatabaseSQLPlaygroundLog from './DatabaseSQLPlaygroundLog.vue';
import DatabaseTableSchemaDialog from './DatabaseTableSchemaDialog.vue';
import SQLResult from './SQLResult.vue';

export default {
	name: 'DatabaseSQLPlayground',
	props: ['name'],
	components: {
		FTabs: Tabs,
		DatabaseToolWrapper,
		SQLResultTable,
		SQLResult,
		SQLCodeEditor,
		DatabaseSQLPlaygroundLog,
		DatabaseTableSchemaDialog
	},
	data() {
		return {
			tabIndex: 0,
			query: '',
			commit: false,
			execution_successful: null,
			data: null,
			errorMessage: null,
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
					this.execution_successful = data?.message?.success || false;
					if (!this.execution_successful) {
						this.errorMessage = data?.message?.data || 'Unknown error';
						this.data = [];
					} else {
						this.data = data?.message?.data ?? [];
						this.errorMessage = null;
					}
					this.tabIndex = 0; // reset tab index for results
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
		sqlResultTabs() {
			if (!this.data || !this.data.length) return [];
			let data = [];
			let queryNo = 1;
			for (let i = 0; i < this.data.length; i++) {
				data.push({
					label: `Query ${queryNo++}`,
					...this.data[i]
				});
			}
			return data;
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
		},
		prettifySQLError(msg) {
			if (typeof msg !== 'string') return null;
			// if error message in (state, message) format, try to parse it
			const regex = /\((\d+),\s*['"](.*?)['"]\)/;
			const match = msg.match(regex);

			if (match) {
				const statusCode = match[1];
				const errorMessage = match[2];
				return `#${statusCode} - ${errorMessage}`;
			} else {
				return msg;
			}
		}
	}
};
</script>
