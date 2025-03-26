<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div
			class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
		>
			<div class="flex flex-row items-center gap-2">
				<!-- Title -->
				<Breadcrumbs
					:items="[
						{ label: 'Dev Tools', route: '/sql-playground' }, // Dev tools has no seperate page as its own, so it doesn't need a different route
						{ label: 'SQL Playground', route: '/sql-playground' },
					]"
				/>
				<!-- Actions -->
				<FormControl
					class="w-min-[200px] cursor-pointer"
					type="select"
					:options="[
						{
							label: 'Read Only&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;',
							value: 'read-only',
						},
						{
							label: 'Read Write&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;',
							value: 'read-write',
						},
					]"
					size="sm"
					variant="outline"
					v-model="mode"
				/>
			</div>
			<div class="flex flex-row gap-2">
				<LinkControl
					class="cursor-pointer"
					:options="{
						doctype: 'Site',
						filters: { status: ['!=', 'Archived'] },
					}"
					placeholder="Select a site"
					v-model="site"
				/>
				<Button
					icon="refresh-ccw"
					variant="subtle"
					:loading="site && !isAutoCompletionReady"
					:disabled="!site"
					@click="
						() =>
							fetchTableSchemas({
								reload: true,
							})
					"
				>
					<span class="md:hidden">Schema</span>
					<span class="hidden md:inline">Refresh Schema</span>
				</Button>
			</div>
		</div>
	</Header>
	<div class="m-5">
		<!-- body -->
		<div
			v-if="!site"
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
		>
			Select a site to get started
		</div>
		<div class="mt-2 flex flex-col" v-else>
			<div class="overflow-hidden rounded border">
				<SQLCodeEditor
					v-model="query"
					:schema="sqlSchemaForAutocompletion"
					@codeSelected="handleCodeSelected"
					@codeUnselected="handleCodeUnselected"
				/>
			</div>
			<div class="mt-2 flex flex-row items-center justify-between">
				<div class="flex gap-2">
					<Button
						iconLeft="table"
						@click="toggleTableSchemasDialog"
						:disabled="!isAutoCompletionReady"
						>Tables</Button
					>
					<Button iconLeft="file-text" @click="toggleLogsDialog">Logs</Button>
				</div>

				<div class="flex gap-2">
					<Button
						v-if="selectedQuery"
						@click="runSelectedSQLQuery"
						:loading="$resources.runSQLQuery.loading"
						iconLeft="play"
						variant="outline"
					>
						Run Selected Query
					</Button>
					<Button
						@click="() => runSQLQuery()"
						:loading="$resources.runSQLQuery.loading"
						iconLeft="play"
						variant="solid"
						>Run Query</Button
					>
				</div>
			</div>
			<div
				class="mt-4"
				v-if="!$resources.runSQLQuery.loading && (data || errorMessage)"
			>
				<div v-if="errorMessage" class="output-container">
					<pre class="mb-4 text-sm" v-if="failedQuery">{{ failedQuery }}</pre>
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
						<template #tab-panel="{ tab }">
							<div class="pt-5">
								<SQLResult :result="tab" />
							</div>
						</template>
					</FTabs>
				</div>
			</div>
		</div>

		<DatabaseSQLPlaygroundLog
			v-if="this.site"
			:site="this.site"
			v-model="showLogsDialog"
			@rerunQuery="rerunQuery"
		/>
		<DatabaseTableSchemaDialog
			v-if="this.site"
			:site="this.site"
			:tableSchemas="$resources.tableSchemas?.data?.message?.data ?? {}"
			v-model="showTableSchemasDialog"
			:showSQLActions="true"
			@runSQLQuery="runSQLQueryForViewingTable"
		/>
	</div>
</template>
<style scoped>
.output-container {
	@apply rounded border p-4 text-base text-gray-700;
}
</style>
<script>
import { toast } from 'vue-sonner';
import Header from '../../../components/Header.vue';
import { Tabs, Breadcrumbs } from 'frappe-ui';
import SQLResultTable from '../../../components/devtools/database/ResultTable.vue';
import SQLCodeEditor from '../../../components/devtools/database/SQLCodeEditor.vue';
import { confirmDialog } from '../../../utils/components';
import DatabaseSQLPlaygroundLog from '../../../components/devtools/database/DatabaseSQLPlaygroundLog.vue';
import DatabaseTableSchemaDialog from '../../../components/devtools/database/DatabaseTableSchemaDialog.vue';
import SQLResult from '../../../components/devtools/database/SQLResult.vue';
import LinkControl from '../../../components/LinkControl.vue';
import { getToastErrorMessage } from '../../../utils/toast';

export default {
	name: 'DatabaseSQLPlayground',
	components: {
		Header,
		Breadcrumbs,
		FTabs: Tabs,
		SQLResultTable,
		SQLResult,
		SQLCodeEditor,
		DatabaseSQLPlaygroundLog,
		DatabaseTableSchemaDialog,
		LinkControl,
	},
	data() {
		return {
			site: null,
			tabIndex: 0,
			query: '',
			selectedQuery: null,
			commit: false,
			execution_successful: null,
			data: null,
			errorMessage: null,
			failedQuery: null,
			mode: 'read-only',
			showLogsDialog: false,
			showTableSchemasDialog: false,
		};
	},
	mounted() {},
	watch: {
		query() {
			window.localStorage.setItem(
				`sql_playground_query_${this.site}`,
				this.query,
			);
		},
		site(site_name) {
			// reset state
			this.execution_successful = null;
			this.data = null;
			this.errorMessage = null;
			this.failedQuery = null;
			this.mode = 'read-only';
			this.showLogsDialog = false;
			this.showTableSchemasDialog = false;

			// recover query and fetch table schemas
			this.query =
				window.localStorage.getItem(`sql_playground_query_${this.site}`) || '';
			this.fetchTableSchemas({
				site_name: site_name,
			});
		},
	},
	resources: {
		runSQLQuery() {
			return {
				url: 'press.api.client.run_doc_method',
				onSuccess: (data) => {
					this.execution_successful = data?.message?.success || false;
					if (!this.execution_successful) {
						this.errorMessage = data?.message?.data ?? 'Unknown error';
						this.failedQuery = data?.message?.failed_query ?? '';
						this.data = [];
					} else {
						this.data = data?.message?.data ?? [];
						this.errorMessage = null;
					}
					this.tabIndex = 0; // reset tab index for results
				},
				onError: (e) => {
					toast.error(getToastErrorMessage(e, 'Failed to run SQL query'));
				},
				auto: false,
			};
		},
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				},
			};
		},
	},
	computed: {
		sqlSchemaForAutocompletion() {
			const tableSchemas =
				this.$resources.tableSchemas?.data?.message?.data ?? {};
			if (!tableSchemas || !Object.keys(tableSchemas).length) return null;
			let childrenSchemas = {};
			for (const tableName in tableSchemas) {
				childrenSchemas[tableName] = {
					self: { label: tableName, type: 'table' },
					children: tableSchemas[tableName].columns.map((x) => ({
						label: x.column,
						type: 'column',
						detail: x.data_type,
					})),
				};
			}
			return {
				self: { label: 'SQL Schema', type: 'schema' },
				children: childrenSchemas,
			};
		},
		isAutoCompletionReady() {
			if (this.$resources.tableSchemas.loading) return false;
			if (this.$resources.tableSchemas?.data?.message?.loading) return false;
			if (!this.$resources.tableSchemas?.data?.message?.data) return false;
			if (this.$resources.tableSchemas?.data?.message?.data == {}) return false;
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
					...this.data[i],
				});
			}
			return data;
		},
	},
	methods: {
		handleCodeSelected(selectedCode) {
			this.selectedQuery = selectedCode;
		},
		handleCodeUnselected() {
			this.selectedQuery = null;
		},
		fetchTableSchemas({ site_name = null, reload = false } = {}) {
			if (!site_name) site_name = this.site;
			if (!site_name) return;
			this.$resources.tableSchemas.submit({
				dt: 'Site',
				dn: site_name,
				method: 'fetch_database_table_schema',
				args: {
					reload,
				},
			});
		},
		runSQLQuery(ignore_validation = false, run_selected_query = false) {
			if (!this.query) return;
			if (this.mode === 'read-only' || ignore_validation) {
				this.$resources.runSQLQuery.submit({
					dt: 'Site',
					dn: this.site,
					method: 'run_sql_query_in_database',
					args: {
						query: run_selected_query ? this.selectedQuery : this.query,
						commit: this.mode === 'read-write',
					},
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
						this.runSQLQuery(true, run_selected_query);
						hide();
					},
				},
			});
		},
		runSelectedSQLQuery() {
			if (!this.selectedQuery) {
				return;
			}
			confirmDialog({
				title: 'Verify Query',
				message: `
Are you sure you want to run the query?
<br>
<pre class="mt-2 max-h-52 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-700">${this.selectedQuery}</pre>
				`,
				primaryAction: {
					label: 'Run Query',
					variant: 'solid',
					onClick: ({ hide }) => {
						this.runSQLQuery(false, true);
						hide();
					},
				},
			});
		},
		toggleLogsDialog() {
			this.showLogsDialog = !this.showLogsDialog;
		},
		toggleTableSchemasDialog() {
			if (!this.isAutoCompletionReady) {
				toast.error('Table schemas are still loading. Please wait.');
				return;
			}
			this.showTableSchemasDialog = !this.showTableSchemasDialog;
		},
		rerunQuery(query) {
			this.query = query;
			this.showLogsDialog = false;
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
		},
	},
};
</script>
