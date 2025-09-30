<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div
			class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
		>
			<div class="flex flex-row items-center gap-2">
				<!-- Title -->
				<Breadcrumbs
					:items="[
						{ label: 'Dev Tools', route: '/binlog-browser' },
						{ label: 'Binlog Browser', route: '/binlog-browser' },
					]"
				/>
			</div>
			<LinkControl
				class="cursor-pointer"
				:options="{ doctype: 'Site', filters: { status: 'Active' } }"
				placeholder="Select a site"
				v-model="site"
			/>
		</div>
	</Header>
	<div class="m-5">
		<div
			v-if="!site"
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
		>
			Select a site to get started
		</div>
		<div class="mt-2 flex flex-col" v-else>
			<!-- Time and Query Selector -->
			<div class="flex flex-row items-center justify-between gap-2">
				<div class="flex flex-row items-center gap-2">
					<div class="text-base">Query</div>
					<FormControl
						type="select"
						:options="[
							{ label: 'ALL     ', value: 'ALL' },
							{ label: 'INSERT  ', value: 'INSERT' },
							{ label: 'UPDATE  ', value: 'UPDATE' },
							{ label: 'DELETE  ', value: 'DELETE' },
							{ label: 'SELECT  ', value: 'SELECT' },
							{ label: 'OTHER   ', value: 'OTHER' },
						]"
						size="sm"
						variant="outline"
						placeholder="Query Type"
						v-model="type"
					/>
				</div>
				<div class="flex flex-row items-center gap-2">
					<div class="max-w-[11rem] text-base">
						<DateTimePicker
							v-model="start"
							variant="outline"
							placeholder="Start Time"
							:disabled="false"
						/>
					</div>

					<FeatherIcon name="arrow-right" class="h-5 w-5 stroke-gray-700" />
					<div class="max-w-[11rem] text-base">
						<DateTimePicker
							v-model="end"
							variant="outline"
							placeholder="End Time"
							:disabled="false"
						/>
					</div>
				</div>
			</div>
			<!-- Timeline chart -->
			<BarChart
				:key="barChartData"
				:data="barChartData"
				:showCard="true"
				:loading="this.$resources.timeline?.loading ?? true"
				class="mt-3 h-[15.5rem]"
			/>
			<!-- Query Option -->
			<div class="mt-3 flex flex-row items-center justify-between gap-2">
				<div class="flex flex-row items-center gap-2">
					<div class="text-base">Table</div>
					<FormControl
						type="select"
						:options="
							tables.map((table) => ({
								label: table,
								value: table,
							}))
						"
						size="sm"
						variant="outline"
						placeholder="Selected Table"
						v-model="selectedTable"
					/>
					<Button
						variant="outline"
						theme="gray"
						size="sm"
						@click="this.showTypeColumn = !this.showTypeColumn"
						:iconLeft="this.showTypeColumn ? 'eye' : 'eye-off'"
					>
						Query Type
					</Button>
					<Button
						variant="outline"
						theme="gray"
						size="sm"
						@click="this.showTableColumn = !this.showTableColumn"
						:iconLeft="this.showTableColumn ? 'eye' : 'eye-off'"
					>
						Table Name
					</Button>
				</div>

				<div class="flex flex-row items-center gap-2">
					<FormControl
						type="text"
						size="sm"
						variant="outline"
						placeholder="Search keywords"
						v-model="searchString"
					/>
					<Button
						variant="solid"
						theme="gray"
						size="sm"
						@click="searchBinlogs"
						:loading="
							this.$resources?.searchBinlogs?.loading ||
							this.$resources?.fetchQueriesFromBinlog?.loading
						"
						loadingText="Searching"
						iconLeft="search"
					>
						Search
					</Button>
				</div>
			</div>
			<!-- Result Table -->
			<div class="mt-3">
				<div
					v-if="!this.searchResultReady"
					class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
				>
					Search for binlogs to see results
				</div>
				<div
					v-else-if="this.$resources?.searchBinlogs?.loading"
					class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
				>
					<Spinner class="w-4" /> Searching for binlogs...
				</div>
				<BinlogResultTable
					v-else
					:loadingData="this.$resources?.fetchQueriesFromBinlog?.loading"
					:loadData="this.fetchQueries"
					:columns="this.tableColumns"
					:data="this.tableRows"
					:isTruncateText="true"
					:truncateLength="120"
					:noOfRows="queryIds.length"
					:fullViewFormatters="fullViewFormatters"
					:cellFormatters="cellFormatters"
					:alignColumns="{
						'Event Size': 'center',
						Timestamp: 'center',
					}"
				/>
			</div>
		</div>
	</div>
</template>
<script>
import Header from '../../../components/Header.vue';
import { Tabs, Breadcrumbs, Select, FeatherIcon } from 'frappe-ui';
import { formatValue } from '../../../utils/format';
import LinkControl from '../../../components/LinkControl.vue';
import BinlogResultTable from '../../../components/devtools/database/BinlogResultTable.vue';

export default {
	name: 'BinlogBrowser',
	components: {
		Header,
		Breadcrumbs,
		Tabs,
		LinkControl,
		Select,
		BinlogResultTable,
	},
	data() {
		return {
			site: null,
			errorMessage: null,
			data: null,
			start: null,
			end: null,
			type: 'ALL',
			selectedTable: 'All Tables',
			searchString: '',
			queryIds: [],
			result: [],
			searchResultReady: false,
			showTypeColumn: false,
			showTableColumn: false,
		};
	},
	mounted() {
		const now = new Date();
		this.end = now.toLocaleString();
		const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
		this.start = oneHourAgo.toLocaleString();

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
			this.$resources.site.submit();
			this.fetchBinlogTimeline();
		},
		type() {
			this.fetchBinlogTimeline();
		},
		start() {
			this.fetchBinlogTimeline();
		},
		end() {
			this.fetchBinlogTimeline();
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
		timeline() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message) {
						this.resetSearch();
					}
				},
			};
		},
		searchBinlogs() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message) {
						this.queryIds = [];
						this.result = [];
						let rowIds = data?.message;
						let binlogs = Object.keys(rowIds).sort();
						for (let i = 0; i < binlogs.length; i++) {
							let binlogRowIds = rowIds[binlogs[i]];
							for (let j = 0; j < binlogRowIds.length; j++) {
								this.queryIds.push(`${binlogs[i]}:${binlogRowIds[j]}`);
							}
						}
						this.searchResultReady = true;
					}
				},
			};
		},
		fetchQueriesFromBinlog() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: (data) => {
					if (data?.message) {
						let binlogs = Object.keys(data.message);
						binlogs.sort();
						this.result = [];
						for (let i = 0; i < binlogs.length; i++) {
							let binlogRowIds = Object.keys(data.message[binlogs[i]]);
							binlogRowIds.sort();
							for (let j = 0; j < binlogRowIds.length; j++) {
								let queryInfo = data.message[binlogs[i]][binlogRowIds[j]];
								this.result.push([
									queryInfo[1],
									queryInfo[4],
									queryInfo[0],
									new Date(queryInfo[5] * 1000).toLocaleString(),
									queryInfo[2],
								]);
							}
						}
					}
				},
			};
		},
	},
	methods: {
		fetchBinlogTimeline() {
			if (!this.start || !this.end || !this.site) return;
			if (this.$resources.timeline?.loading ?? true) return;
			this.$resources.timeline.submit({
				dt: 'Site',
				dn: this.site,
				method: 'fetch_binlog_timeline',
				args: {
					start: parseInt(new Date(this.start).getTime() / 1000),
					end: parseInt(new Date(this.end).getTime() / 1000),
					query_type: this.type === 'ALL' ? null : this.type,
				},
			});
		},
		searchBinlogs() {
			this.$resources.searchBinlogs.submit({
				dt: 'Site',
				dn: this.site,
				method: 'search_binlogs',
				args: {
					start: parseInt(new Date(this.start).getTime() / 1000),
					end: parseInt(new Date(this.end).getTime() / 1000),
					query_type: this.type === 'ALL' ? null : this.type,
					table:
						this.selectedTable === 'All Tables' ? null : this.selectedTable,
					search_string: this.searchString,
				},
			});
		},
		fetchQueries(start, end) {
			let lastQueryIndex = this.result.length;
			if (lastQueryIndex >= this.queryIds.length) {
				return;
			}
			if (this.$resources.fetchQueriesFromBinlog?.loading ?? true) return;

			// Load 50 queries at a time
			const queriesToLoad = this.queryIds.slice(start, end);
			let rowIds = {};
			queriesToLoad.forEach((q) => {
				const [binlog, rowId] = q.split(':');
				if (!rowIds[binlog]) {
					rowIds[binlog] = [];
				}
				rowIds[binlog].push(parseInt(rowId));
			});

			if (Object.keys(rowIds).length > 0) {
				this.$resources.fetchQueriesFromBinlog.submit({
					dt: 'Site',
					dn: this.site,
					method: 'fetch_queries_from_binlog',
					args: {
						row_ids: rowIds,
					},
				});
			}
		},
		resetSearch() {
			this.queryIds = [];
			this.result = [];
			this.searchResultReady = false;
		},
	},
	computed: {
		isRequiredInformationReceived() {
			if (this.$resources.site?.loading ?? true) return false;
			return true;
		},
		timeline() {
			return this.$resources?.timeline?.data?.message ?? {};
		},
		tables() {
			return ['All Tables', ...(this.timeline?.tables ?? [])];
		},
		barChartData() {
			if (!this.timeline?.labels) {
				return {
					datasets: [],
					labels: [],
				};
			}
			return {
				datasets: this.timeline.datasets,
				labels: this.timeline.labels.map((label) => {
					const date = new Date(label * 1000);
					return date.toLocaleString('default', {
						day: '2-digit',
						month: 'short',
						hour: '2-digit',
						minute: '2-digit',
					});
				}),
			};
		},
		tableColumns() {
			let columns = ['Type', 'Table', 'Query', 'Timestamp', 'Event Size'];
			if (!this.showTypeColumn && !this.showTableColumn) {
				columns = columns.slice(2);
			} else if (!this.showTypeColumn) {
				columns = columns.slice(1);
			} else if (!this.showTableColumn) {
				columns = columns.filter((col) => col !== 'Table');
			}
			return columns;
		},
		tableRows() {
			if (!this.result) return [];
			let result = this.result;
			if (!this.showTypeColumn && !this.showTableColumn) {
				result = result.map((row) => row.slice(2));
			} else if (!this.showTypeColumn) {
				result = result.map((row) => [row[1], row[2], row[3]]);
			} else if (!this.showTableColumn) {
				result = result.map((row) => [row[0], row[2], row[3]]);
			}
			return result;
		},
		cellFormatters() {
			return {
				'Event Size': (v) => formatValue(v, 'bytes'),
			};
		},
		fullViewFormatters() {
			return {
				Query: (v) => formatValue(v, 'sql'),
			};
		},
	},
};
</script>
