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
						{ label: 'Database Analyzer', route: '/database-analyzer' }
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
								reload: true
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
						<Button @click="optimizeTable"> View Details </Button>
						<Button @click="optimizeTable"> Optimize Table </Button>
					</div>
				</div>

				<!-- TODO: Make it a separate component to reuse it  -->
				<!-- Slider -->
				<div
					class="mb-4 mt-4 flex h-7 w-full items-start justify-start overflow-clip rounded border bg-gray-50 pl-0"
				>
					<div
						class="h-7"
						:style="{
							backgroundColor: '#E86C13',
							width: `${databaseSizeBreakup.data_size_percentage}%`
						}"
					></div>
					<div
						class="h-7"
						:style="{
							backgroundColor: '#34BAE3',
							width: `${databaseSizeBreakup.index_size_percentage}%`
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
						><span class="ml-auto text-sm text-gray-800"
							>{{ this.databaseSizeBreakup.data_size }} MB</span
						>
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
							>{{ this.databaseSizeBreakup.index_size }} MB</span
						>
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
							>{{ this.databaseSizeBreakup.free_size }} MB</span
						>
					</div>
				</div>
			</div>

			<!-- Queries Information -->
			<ToggleContent
				class="mt-5"
				label="SQL Query Analysis"
				subLabel="Check the concerning queries that might be affecting your database performance"
			>
				<FTabs
					class="mt-1"
					:tabs="queryTabs"
					v-model="queryTabIndex"
					v-if="queryTabs.length"
				>
					<template #default="{ tab }">
						<ResultTable
							:columns="tab.columns"
							:data="tab.data"
							:enableCSVExport="false"
							:borderLess="true"
						/>
					</template>
				</FTabs>
			</ToggleContent>

			<!-- Indexes Information -->
			<ToggleContent
				class="mt-3"
				label="Database Index Analysis"
				subLabel="Analyze the indexes of the database"
			>
				<FTabs
					class="mt-1"
					:tabs="databaseIndexesTab"
					v-model="dbIndexTabIndex"
					v-if="databaseIndexesTab.length"
				>
					<template #default="{ tab }">
						<ResultTable
							:columns="tab.columns"
							:data="tab.data"
							:enableCSVExport="false"
							:borderLess="true"
						/>
					</template>
				</FTabs>
			</ToggleContent>

			<!-- <ObjectList :options="tableAnalysisTableOptions" /> -->
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
import { h } from 'vue';
import { toast } from 'vue-sonner';
import ToggleContent from '../../../components/ToggleContent.vue';
import ResultTable from '../../../components/devtools/database/ResultTable.vue';

export default {
	name: 'DatabaseAnalyzer',
	components: {
		Header,
		Breadcrumbs,
		FTabs: Tabs,
		LinkControl,
		ObjectList,
		ToggleContent,
		ResultTable
	},
	data() {
		return {
			site: null,
			errorMessage: null,
			optimizeTableJobName: null,
			queryTabIndex: 0,
			dbIndexTabIndex: 0
		};
	},
	mounted() {},
	watch: {
		site(site_name) {
			// reset state
			this.data = null;
			this.errorMessage = null;
			this.fetchTableSchemas({
				site_name: site_name
			});
			this.$resources.site.reload();
			this.$resources.databasePerformanceReport.reload();
		}
	},
	resources: {
		site() {
			return {
				url: 'press.api.client.get',
				initialData: {},
				makeParams: () => {
					return { doctype: 'Site', name: this.site };
				},
				auto: false
			};
		},
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				}
			};
		},
		optimizeTable() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message) {
						if (data?.message?.success) {
							toast.success(data?.message?.message);
						} else {
							toast.error(data?.message?.message);
						}
						this.optimizeTableJobName = data?.message?.job_name;
					}
				}
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
						method: 'get_database_performance_report'
					};
				},
				auto: false
			};
		}
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
			return true;
		},
		tableSchemas() {
			if (!this.isRequiredInformationReceived) return [];
			return this.$resources.tableSchemas?.data?.message?.data;
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
					no_of_columns: table.columns.length
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
									}
								},
								[row.table_name]
							);
						}
					},
					{
						label: 'Size (MB)',
						fieldname: 'total_size_mb',
						width: 0.5
					},
					{
						label: 'No of Columns',
						fieldname: 'no_of_columns',
						width: 0.5
					}
				]
			};
		},
		databaseSizeBreakup() {
			if (!this.isRequiredInformationReceived) return null;
			let data_size = this.tableSizeInfo.reduce(
				(a, b) => a + parseFloat(b.data_size_mb),
				0
			);
			data_size = data_size.toFixed(2);

			let index_size = this.tableSizeInfo.reduce(
				(a, b) => a + parseFloat(b.index_size_mb),
				0
			);
			index_size = index_size.toFixed(2);

			let database_size_limit = this.site_info.current_plan.max_database_usage;

			return {
				data_size,
				index_size,
				database_size_limit,
				free_size: database_size_limit - data_size - index_size,
				data_size_percentage: parseInt((data_size / database_size_limit) * 100),
				index_size_percentage: parseInt(
					(index_size / database_size_limit) * 100
				)
			};
		},
		queryTabs() {
			if (!this.isRequiredInformationReceived) return [];
			const result = this.$resources.databasePerformanceReport?.data?.message;
			if (!result) return [];
			let prepared_result = [
				{
					label: 'Slow Queries',
					columns: ['Rows Examined', 'Rows Sent', 'Calls', 'Duration', 'Query'],
					data: result['slow_queries'].map(e => {
						return [e.rows_examined, e.rows_sent, e.count, e.duration, e.query];
					})
				},
				{
					label: 'Time Consuming Queries',
					columns: ['Percentage', 'Calls', 'Avg Time (ms)', 'Query'],
					data: result['top_10_time_consuming_queries'].map(e => {
						return [
							Math.round(e['percent'], 1),
							e['calls'],
							e['avg_time_ms'],
							e['query']
						];
					})
				},
				{
					label: 'Full Table Scan',
					columns: ['Rows Examined', 'Rows Sent', 'Calls', 'Query'],
					data: result['top_10_queries_with_full_table_scan'].map(e => {
						return [
							e['rows_examined'],
							e['rows_sent'],
							e['calls'],
							e['example']
						];
					})
				}
			];
			return prepared_result;
		},
		databaseIndexesTab() {
			if (!this.isRequiredInformationReceived) return [];
			const result = this.$resources.databasePerformanceReport?.data?.message;
			if (!result) return [];
			let prepared_result = [
				{
					label: 'Redundant Indexes',
					columns: [
						'Table Name',
						'Dominant Index',
						'Dominant Index Columns',
						'Redundant Index',
						'Redundant Index Columns'
					],
					data: result['redundant_indexes'].map(e => {
						return [
							e['table_name'],
							e['dominant_index_name'],
							e['dominant_index_columns'],
							e['redundant_index_name'],
							e['redundant_index_columns']
						];
					})
				},
				{
					label: 'Unused Indexes',
					columns: ['Table Name', 'Index Name'],
					data: result['unused_indexes'].map(e => {
						return [e['table_name'], e['index_name']];
					})
				}
			];
			console.log(prepared_result);
			return prepared_result;
		}
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
					reload
				}
			});
		},
		optimizeTable() {
			this.$resources.optimizeTable.submit({
				dt: 'Site',
				dn: this.site,
				method: 'optimize_tables'
			});
		}
	}
};
</script>
