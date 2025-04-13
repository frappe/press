<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div
			class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
		>
			<div class="flex flex-row items-center gap-2">
				<!-- Title -->
				<Breadcrumbs
					:items="[
						{ label: 'Dev Tools', route: '/database-analyzer' },
						{ label: 'Database Analyzer', route: '/database-analyzer' },
					]"
				/>
			</div>
			<div class="flex flex-row gap-2">
				<LinkControl
					class="cursor-pointer"
					:options="{ doctype: 'Site', filters: { status: 'Active' } }"
					placeholder="Select a site"
					v-model="site"
				/>
				<Button
					iconLeft="refresh-ccw"
					variant="subtle"
					:loading="site && !isRequiredInformationReceived"
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
		<div class="mt-2 flex flex-col" v-if="isRequiredInformationReceived">
			<!-- Database Size Analyzer -->
			<div>
				<div class="flex flex-row items-center justify-between">
					<p class="text-base font-medium text-gray-800">
						Database Size Breakup
					</p>
					<div class="flex flex-row gap-2">
						<Button @click="this.showTableSchemaSizeDetailsDialog = true">
							View Details
						</Button>
						<Button
							@click="optimizeTable"
							:loading="this.$resources.optimizeTable.loading"
						>
							Optimize Table
						</Button>
					</div>
				</div>

				<!-- Slider -->
				<div
					class="mb-4 mt-4 flex h-7 w-full cursor-pointer items-start justify-start overflow-clip rounded border bg-gray-50 pl-0"
					@click="showTableSchemaSizeDetailsDialog = true"
				>
					<div
						class="h-7"
						:style="{
							backgroundColor: '#E86C13',
							width: `${databaseSizeBreakup.data_size_percentage}%`,
						}"
					></div>
					<div
						class="h-7"
						:style="{
							backgroundColor: '#34BAE3',
							width: `${databaseSizeBreakup.index_size_percentage}%`,
						}"
					></div>
				</div>
				<!-- Table -->
				<div
					class="full flex w-full flex-col items-start justify-start overflow-y-auto rounded px-1.5"
				>
					<div class="flex w-full items-center justify-start gap-x-2 py-3">
						<div
							class="h-2 w-2 rounded-full"
							style="background-color: #e86c13"
						></div>
						<span class="text-sm text-gray-800">Data Size</span
						><span class="ml-auto text-sm text-gray-800">{{
							formatSizeInMB(this.databaseSizeBreakup.data_size)
						}}</span>
					</div>
					<div
						class="flex w-full items-center justify-start gap-x-2 border-t py-3"
					>
						<div
							class="h-2 w-2 rounded-full"
							style="background-color: #34bae3"
						></div>
						<span class="text-sm text-gray-800">Index Size</span
						><span class="ml-auto text-sm text-gray-800"
							>{{ formatSizeInMB(this.databaseSizeBreakup.index_size) }}
						</span>
					</div>
					<div
						class="flex w-full items-center justify-start gap-x-2 border-t py-3"
					>
						<div
							class="h-2 w-2 rounded-full"
							style="background-color: #e2e2e2"
						></div>
						<span class="text-sm text-gray-800">Free Space</span
						><span class="ml-auto text-sm text-gray-800"
							>{{ formatSizeInMB(this.databaseSizeBreakup.free_size) }}
						</span>
					</div>
				</div>
			</div>

			<!-- Database Processes -->
			<ToggleContent
				class="mt-3"
				label="Database Processes"
				subLabel="Analyze the processes of the database"
			>
				<template #actions>
					<div>
						<Button
							:loading="this.$resources.databaseProcesses.loading"
							loading-text="Refreshing"
							icon-left="rotate-ccw"
							@click.stop="this.$resources.databaseProcesses.submit()"
							>Refresh</Button
						>
					</div>
				</template>
				<template #default>
					<div
						v-if="this.$resources.databaseProcesses.loading"
						class="flex h-60 w-full items-center justify-center gap-2 text-base text-gray-700"
					>
						<Spinner class="w-4" /> Loading Database Processes
					</div>
					<ResultTable
						v-else
						class="mt-2"
						:columns="databaseProcesses.columns"
						:data="databaseProcesses.data"
						:alignColumns="alignColumns"
						:cellFormatters="cellFormatters"
						:fullViewFormatters="fullViewFormatters"
						actionHeaderLabel="Kill"
						:actionComponent="DatabaseProcessKillButton"
						:actionComponentProps="{
							site: this.site,
						}"
						:enableCSVExport="false"
						:borderLess="true"
					/>
				</template>
			</ToggleContent>

			<!-- Queries Information -->
			<ToggleContent
				class="mt-3"
				label="SQL Query Analysis"
				subLabel="Check the concerning queries that might be affecting your database performance"
			>
				<div class="mt-1">
					<FTabs
						:tabs="queryTabs"
						v-model="queryTabIndex"
						v-if="queryTabs.length"
					>
						<template #tab-panel="{ tab }">
							<DatabasePerformanceSchemaDisabledNotice
								v-if="
									(tab.label === 'Time Consuming Queries' ||
										tab.label === 'Full Table Scan Queries') &&
									!isPerformanceSchemaEnabled
								"
							/>
							<ResultTable
								v-else
								:columns="tab.columns"
								:data="tab.data"
								:alignColumns="alignColumns"
								:cellFormatters="cellFormatters"
								:fullViewFormatters="fullViewFormatters"
								:enableCSVExport="false"
								:borderLess="true"
								:isTruncateText="true"
							/>
						</template>
					</FTabs>
				</div>
			</ToggleContent>

			<!-- Indexes Information -->
			<ToggleContent
				class="mt-3"
				label="Database Index Analysis"
				subLabel="Analyze the indexes of the database"
			>
				<div class="mt-1">
					<FTabs
						:tabs="databaseIndexesTab"
						v-model="dbIndexTabIndex"
						v-if="databaseIndexesTab.length"
					>
						<template #tab-panel="{ tab }">
							<DatabasePerformanceSchemaDisabledNotice
								v-if="
									(tab.label === 'Unused Indexes' ||
										tab.label === 'Suggested Indexes') &&
									!isPerformanceSchemaEnabled
								"
							/>
							<div v-else-if="tab.label === 'Suggested Indexes'">
								<div
									v-if="
										!isIndexSuggestionTriggered ||
										this.$resources.suggestDatabaseIndexes.loading ||
										this.fetchingDatabaseIndex
									"
									class="flex h-60 flex-col items-center justify-center gap-4"
								>
									<Button
										variant="outline"
										@click="
											() => {
												this.isIndexSuggestionTriggered = true;
												this.$resources.suggestDatabaseIndexes.submit();
											}
										"
										:loading="
											this.$resources.suggestDatabaseIndexes.loading ||
											this.fetchingDatabaseIndex
										"
										>Suggest Indexes</Button
									>
									<p class="text-base text-gray-700">
										This may take a while to analyze
									</p>
								</div>
								<ResultTable
									v-else
									:columns="suggestedDatabaseIndexes.columns"
									:data="suggestedDatabaseIndexes.data"
									:alignColumns="alignColumns"
									:cellFormatters="cellFormatters"
									:fullViewFormatters="fullViewFormatters"
									:enableCSVExport="false"
									:borderLess="true"
									actionHeaderLabel="Add Index"
									:actionComponent="DatabaseAddIndexButton"
									:actionComponentProps="{
										site: this.site,
									}"
									:isTruncateText="true"
								/>
							</div>
							<ResultTable
								v-else
								:columns="tab.columns"
								:data="tab.data"
								:alignColumns="alignColumns"
								:cellFormatters="cellFormatters"
								:fullViewFormatters="fullViewFormatters"
								:isTruncateText="true"
								:enableCSVExport="false"
								:borderLess="true"
							/>
						</template>
					</FTabs>
				</div>
			</ToggleContent>

			<DatabaseTableSchemaSizeDetailsDialog
				v-if="this.site"
				:site="this.site"
				:tableSchemas="tableSchemas"
				v-model="showTableSchemaSizeDetailsDialog"
				:viewSchemaDetails="viewTableSchemaDetails"
			/>

			<DatabaseTableSchemaDialog
				v-if="this.site"
				:site="this.site"
				:tableSchemas="tableSchemas"
				:pre-selected-schema="preSelectedSchemaForSchemaDialog"
				v-model="showTableSchemasDialog"
			/>
		</div>
		<div
			v-else-if="!site"
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
		>
			Select a site to get started
		</div>
		<div
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			v-else
		>
			<Spinner class="w-4" /> Loading Table Schemas
		</div>
	</div>
</template>
<script>
import Header from '../../../components/Header.vue';
import { Tabs, Breadcrumbs } from 'frappe-ui';
import LinkControl from '../../../components/LinkControl.vue';
import ObjectList from '../../../components/ObjectList.vue';
import { h, markRaw } from 'vue';
import { toast } from 'vue-sonner';
import { formatValue } from '../../../utils/format';
import ToggleContent from '../../../components/ToggleContent.vue';
import ResultTable from '../../../components/devtools/database/ResultTable.vue';
import DatabaseProcessKillButton from '../../../components/devtools/database/DatabaseProcessKillButton.vue';
import DatabaseTableSchemaDialog from '../../../components/devtools/database/DatabaseTableSchemaDialog.vue';
import DatabaseTableSchemaSizeDetailsDialog from '../../../components/devtools/database/DatabaseTableSchemaSizeDetailsDialog.vue';
import DatabaseAddIndexButton from '../../../components/devtools/database/DatabaseAddIndexButton.vue';
import DatabasePerformanceSchemaDisabledNotice from '../../../components/devtools/database/DatabasePerformanceSchemaDisabledNotice.vue';

export default {
	name: 'DatabaseAnalyzer',
	components: {
		Header,
		Breadcrumbs,
		FTabs: Tabs,
		LinkControl,
		ObjectList,
		ToggleContent,
		ResultTable,
		DatabaseTableSchemaDialog,
		DatabaseTableSchemaSizeDetailsDialog,
		DatabaseProcessKillButton,
		DatabasePerformanceSchemaDisabledNotice,
	},
	data() {
		return {
			site: null,
			errorMessage: null,
			isIndexSuggestionTriggered: false,
			queryTabIndex: 0,
			dbIndexTabIndex: 0,
			showTableSchemaSizeDetailsDialog: false,
			preSelectedSchemaForSchemaDialog: null,
			showTableSchemasDialog: false,
			fetchingDatabaseIndex: false,
			DatabaseProcessKillButton: markRaw(DatabaseProcessKillButton),
			DatabaseAddIndexButton: markRaw(DatabaseAddIndexButton),
		};
	},
	mounted() {
		const url = new URL(window.location.href);
		const site_name = url.searchParams.get('site');
		if (site_name) {
			this.site = site_name;
		}
	},
	watch: {
		site(site_name) {
			if (!site_name) return;
			// set site to query param ?site=site_name
			const url = new URL(window.location.href);
			url.searchParams.set('site', site_name);
			window.history.pushState({}, '', url);

			// reset state
			this.data = null;
			this.errorMessage = null;
			this.fetchTableSchemas({
				site_name: site_name,
			});
			this.$resources.site.submit();
			this.$resources.databasePerformanceReport.submit({
				dt: 'Site',
				dn: site_name,
				method: 'get_database_performance_report',
			});
			this.$resources.databaseProcesses.submit({
				dt: 'Site',
				dn: site_name,
				method: 'fetch_database_processes',
			});
		},
	},
	resources: {
		site() {
			return {
				url: 'press.api.client.get',
				initialData: {},
				makeParams: () => {
					return { doctype: 'Site', name: this.site };
				},
				auto: false,
			};
		},
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'fetch_database_table_schema',
					};
				},
				onSuccess: (data) => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				},
			};
		},
		optimizeTable() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message) {
						if (data?.message?.success) {
							toast.success(data?.message?.message);
							this.$router.push(
								`/sites/${this.site}/insights/jobs/${data?.message?.job_name}`,
							);
						} else {
							toast.error(data?.message?.message);
						}
					}
				},
			};
		},
		databasePerformanceReport() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'get_database_performance_report',
					};
				},
				auto: false,
			};
		},
		suggestDatabaseIndexes() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'suggest_database_indexes',
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						this.fetchingDatabaseIndex =
							this.$resources.suggestDatabaseIndexes?.data?.message?.loading ??
							false;
						if (this.fetchingDatabaseIndex) {
							setTimeout(() => {
								this.$resources.suggestDatabaseIndexes.submit();
							}, 5000);
						}
					}
				},
				auto: false,
			};
		},
		databaseProcesses() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'fetch_database_processes',
					};
				},
				auto: false,
			};
		},
	},
	computed: {
		site_info() {
			return this.$resources.site.data;
		},
		isRequiredInformationReceived() {
			if (this.$resources.site?.loading ?? true) return false;
			if (this.$resources.tableSchemas.loading) return false;
			if (this.$resources.tableSchemas?.data?.message?.loading) return false;
			if (!this.$resources.tableSchemas?.data?.message?.data) return false;
			if (this.$resources.tableSchemas?.data?.message?.data == {}) return false;
			if (!this.$resources.databasePerformanceReport?.data?.message)
				return false;
			return true;
		},
		tableSchemas() {
			if (!this.isRequiredInformationReceived) return [];
			let result = this.$resources.tableSchemas?.data?.message?.data ?? [];
			return result;
		},
		tableSizeInfo() {
			if (!this.isRequiredInformationReceived) return [];
			let data = [];
			for (const tableName in this.tableSchemas) {
				const table = this.tableSchemas[tableName];
				data.push({
					table_name: tableName,
					data_size_mb: (table.size.data_length / (1024 * 1024)).toFixed(3),
					index_size_mb: (table.size.index_length / (1024 * 1024)).toFixed(3),
					total_size_mb: (table.size.total_size / (1024 * 1024)).toFixed(3),
					no_of_columns: table.columns.length,
				});
			}
			return data;
		},
		tableAnalysisTableOptions() {
			if (!this.isRequiredInformationReceived) return [];
			return {
				data: () => this.tableSizeInfo,
				hideControls: true,
				columns: [
					{
						label: 'Table Name',
						fieldname: 'table_name',
						width: 0.5,
						type: 'Component',
						component({ row }) {
							return h(
								'div',
								{
									class: 'truncate text-base cursor-copy',
									onClick() {
										if ('clipboard' in navigator) {
											navigator.clipboard.writeText(row.table_name);
											toast.success('Copied to clipboard');
										}
									},
								},
								[row.table_name],
							);
						},
					},
					{
						label: 'Size (MB)',
						fieldname: 'total_size_mb',
						width: 0.5,
					},
					{
						label: 'No of Columns',
						fieldname: 'no_of_columns',
						width: 0.5,
					},
				],
			};
		},
		databaseSizeBreakup() {
			if (!this.isRequiredInformationReceived) return null;
			let data_size = this.tableSizeInfo.reduce(
				(a, b) => a + parseFloat(b.data_size_mb),
				0,
			);
			data_size = data_size.toFixed(2);

			let index_size = this.tableSizeInfo.reduce(
				(a, b) => a + parseFloat(b.index_size_mb),
				0,
			);
			index_size = index_size.toFixed(2);

			let database_size_limit =
				this.site_info.current_plan.max_database_usage.toFixed(2);

			return {
				data_size,
				index_size,
				database_size_limit,
				free_size: (database_size_limit - data_size - index_size).toFixed(2),
				data_size_percentage: parseInt((data_size / database_size_limit) * 100),
				index_size_percentage: parseInt(
					(index_size / database_size_limit) * 100,
				),
			};
		},
		isPerformanceSchemaEnabled() {
			const result = this.$resources.databasePerformanceReport?.data?.message;
			if (!result) return false;
			return result['is_performance_schema_enabled'];
		},
		queryTabs() {
			if (!this.isRequiredInformationReceived) return [];
			const result = this.$resources.databasePerformanceReport?.data?.message;
			if (!result) return [];
			let prepared_result = [
				{
					label: 'Slow Queries',
					columns: ['Rows Examined', 'Rows Sent', 'Calls', 'Duration', 'Query'],
					data: result['slow_queries'].map((e) => {
						return [e.rows_examined, e.rows_sent, e.count, e.duration, e.query];
					}),
				},
				{
					label: 'Time Consuming Queries',
					columns: ['Percentage', 'Calls', 'Avg Time', 'Query'],
					data: result['top_10_time_consuming_queries'].map((e) => {
						return [
							Math.round(e['percent'], 1),
							e['calls'],
							e['avg_time_ms'],
							e['query'],
						];
					}),
				},
				{
					label: 'Full Table Scan Queries',
					columns: ['Rows Examined', 'Rows Sent', 'Calls', 'Query'],
					data: result['top_10_queries_with_full_table_scan'].map((e) => {
						return [e['rows_examined'], e['rows_sent'], e['calls'], e['query']];
					}),
				},
			];
			return prepared_result;
		},
		databaseIndexesTab() {
			if (!this.isRequiredInformationReceived) return [];
			const result = this.$resources.databasePerformanceReport?.data?.message;
			if (!result) return [];
			let prepared_result = [
				{
					label: 'Suggested Indexes',
					columns: ['Table', 'Column', 'Index Name', 'Sample Query'],
					data: [],
				},
				{
					label: 'Redundant Indexes',
					columns: [
						'Table Name',
						'Dominant Index',
						'Dominant Index Columns',
						'Redundant Index',
						'Redundant Index Columns',
					],
					data: result['redundant_indexes'].map((e) => {
						return [
							e['table_name'],
							e['dominant_index_name'],
							e['dominant_index_columns'],
							e['redundant_index_name'],
							e['redundant_index_columns'],
						];
					}),
				},
				{
					label: 'Unused Indexes',
					columns: ['Table Name', 'Index Name'],
					data: result['unused_indexes'].map((e) => {
						return [e['table_name'], e['index_name']];
					}),
				},
			];
			return prepared_result;
		},
		suggestedDatabaseIndexes() {
			if (!this.isRequiredInformationReceived) return [];
			const result =
				this.$resources.suggestDatabaseIndexes?.data?.message?.data ?? [];
			let data = [];
			for (const record of result) {
				for (const index of record.suggested_indexes) {
					data.push([index.table, index.column, record.normalized]);
				}
			}
			return {
				columns: ['Table', 'Column', 'Slow Query'],
				data: data,
			};
		},
		databaseProcesses() {
			if (!this.isRequiredInformationReceived) return null;
			const result = this.$resources.databaseProcesses.data?.message ?? [];
			return {
				columns: ['ID', 'State', 'Time', 'User', 'Host', 'Command', 'Query'],
				data: result.map((e) => {
					return [
						e['id'],
						e['state'],
						e['time'],
						e['db_user'],
						e['db_user_host'],
						e['command'],
						e['query'],
					];
				}),
			};
		},
		cellFormatters() {
			return {
				'Rows Examined': (v) => formatValue(v, 'commaSeperatedNumber'),
				'Rows Sent': (v) => formatValue(v, 'commaSeperatedNumber'),
				Calls: (v) => formatValue(v, 'commaSeperatedNumber'),
				'Avg Time': (v) => formatValue(v, 'durationMilliseconds'),
				Duration: (v) => formatValue(v, 'durationSeconds'),
				Time: (v) => formatValue(v, 'durationSeconds'),
			};
		},
		fullViewFormatters() {
			return {
				Query: (v) => formatValue(v, 'sql'),
			};
		},
		alignColumns() {
			return {
				Percentage: 'right',
				'Rows Examined': 'right',
				'Rows Sent': 'right',
				Calls: 'right',
				'Avg Time': 'right',
				Duration: 'right',
				Time: 'right',
			};
		},
	},
	methods: {
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
		optimizeTable() {
			this.$resources.optimizeTable.submit({
				dt: 'Site',
				dn: this.site,
				method: 'optimize_tables',
			});
		},
		viewTableSchemaDetails(tableName) {
			this.showTableSchemaSizeDetailsDialog = false;
			this.preSelectedSchemaForSchemaDialog = tableName;
			this.showTableSchemasDialog = true;
		},
		formatSizeInMB(mb) {
			try {
				let floatMB = parseFloat(mb);
				if (floatMB < 1) {
					let kb = floatMB * 1024; // Convert MB to KB
					return `${Math.round(kb)} KB`; // Return KB without decimal
				} else if (floatMB < 1024) {
					return `${Math.round(floatMB)} MB`; // Return MB without decimal
				} else {
					let gb = floatMB / 1024; // Convert MB to GB
					return `${gb.toFixed(1)} GB`; // Return GB with 1 decimal
				}
			} catch (error) {
				return `${mb} MB`; // Return MB without decimal
			}
		},
	},
};
</script>
