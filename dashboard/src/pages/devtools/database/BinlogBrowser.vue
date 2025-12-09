<template>
	<div
		:class="{
			'relative h-[100%]':
				this.$resources?.timeline?.loading ||
				binlog_indexer_running ||
				!binlog_indexer_enabled,
		}"
	>
		<Header class="sticky top-0 z-10 bg-white">
			<div
				class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
			>
				<div class="flex flex-row items-center gap-2">
					<Breadcrumbs
						:items="[
							{ label: 'Dev Tools', route: '/binlog-browser' },
							{ label: 'Binlog Browser', route: '/binlog-browser' },
						]"
					/>
				</div>

				<div class="flex flex-row gap-2">
					<Tooltip text="This is an experimental feature">
						<div class="rounded-md bg-purple-100 p-1.5">
							<lucide-flask-conical class="h-4 w-4 text-purple-500" />
						</div>
					</Tooltip>
					<Tooltip text="View documentation">
						<div class="rounded-md bg-gray-100 p-1.5">
							<a
								href="https://docs.frappe.io/cloud/binlog-browser"
								target="_blank"
							>
								<lucide-help-circle class="h-4 w-4" />
							</a>
						</div>
					</Tooltip>
					<Button
						v-if="site"
						:disabled="
							isProcessingQueries ||
							!binlog_indexer_enabled ||
							!isBinlogIndexerAvailable
						"
						@click.prevent="() => (show_binlog_index_status_dialog = true)"
					>
						<div class="flex flex-row items-center gap-1">
							<lucide-package-search class="h-4 w-4" /> Binlogs
						</div>
					</Button>

					<LinkControl
						class="cursor-pointer"
						:options="{ doctype: 'Site', filters: { status: 'Active' } }"
						placeholder="Select a site"
						v-model="site"
					/>
				</div>
			</div>
		</Header>
		<div class="mx-5 my-2.5">
			<div
				v-if="!site"
				class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			>
				Select a site to get started
			</div>
			<div
				v-else-if="!binlog_index_state_loaded"
				class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			>
				<Spinner class="w-4" />
				Loading Binlog Browser...
			</div>
			<div class="mt-2 flex flex-col" v-else>
				<!-- Time and Query Selector -->
				<div class="flex flex-row items-center justify-between gap-2">
					<div class="flex flex-row items-center gap-2">
						<FormControl
							class="w-[13rem]"
							type="select"
							:options="[
								{ label: 'All Query', value: 'ALL' },
								{ label: 'Insert Query', value: 'INSERT' },
								{ label: 'Update Query', value: 'UPDATE' },
								{ label: 'Delete Query', value: 'DELETE' },
								{ label: 'Select Query', value: 'SELECT' },
								{ label: 'Other Query', value: 'OTHER' },
							]"
							size="sm"
							variant="outline"
							placeholder="Query Type"
							v-model="type"
							:disabled="isProcessingQueries"
						/>

						<FormControl
							type="text"
							class="w-[18rem]"
							size="sm"
							variant="outline"
							placeholder="Table Name (% allowed)"
							v-model="tableName"
							:disabled="isProcessingQueries"
						/>

						<div class="w-full flex flex-row items-center gap-2">
							<div class="text-base">Event Size</div>
							<FormControl
								class="w-[8rem]"
								type="select"
								:options="[
									{
										label: '',
										value: '',
									},
									{
										label: 'less than',
										value: 'lt',
									},
									{
										label: 'greater than',
										value: 'gt',
									},
								]"
								size="sm"
								variant="outline"
								:disabled="isProcessingQueries"
								v-model="event_size_comparator"
								placeholder="Comparator"
							/>
							<FormControl
								v-if="event_size_comparator"
								type="number"
								size="sm"
								variant="outline"
								placeholder="size"
								class="w-[8rem]"
								v-model="event_size"
								:disabled="isProcessingQueries"
							/>
							<div v-if="event_size_comparator" class="text-base">bytes</div>
						</div>
					</div>
					<div class="flex flex-row items-center gap-2">
						<div class="w-[12rem] text-base" :autoClose="false">
							<DateTimePicker
								v-model="start"
								variant="outline"
								placeholder="Start Time"
								:disabled="isProcessingQueries"
								:disableTextInput="true"
								:clearable="false"
								:maxDateTime="end"
							/>
						</div>
						<FeatherIcon name="arrow-right" class="h-5 w-5 stroke-gray-700" />
						<div class="w-[12rem] text-base" :autoClose="true">
							<DateTimePicker
								v-model="end"
								variant="outline"
								placeholder="End Time"
								:disabled="isProcessingQueries"
								:disableTextInput="true"
								:clearable="false"
								:minDateTime="start"
								:maxDateTime="Date()"
							/>
						</div>
					</div>
				</div>
				<!-- Timeline chart -->
				<div class="max-w-100 pt-2">
					<BinlogBrowserChart :data="barChartData" @zoomEvent="onZoomEvent" />
				</div>
				<div class="relative">
					<!-- Query Option -->
					<div class="flex flex-row items-center justify-end gap-2">
						<TextInput
							type="text"
							size="sm"
							variant="outline"
							placeholder="Search Phrase (Optional)"
							class="w-[12rem]"
							v-model="searchString"
							:disabled="isProcessingQueries"
							@keydown.enter.prevent="searchBinlogs"
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

					<!-- Result Table -->
					<div class="mt-3" v-if="isBinlogSearchAccessible">
						<div
							v-if="this.$resources?.searchBinlogs?.loading"
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

					<!-- Block  -->
					<div
						class="z-1000 h-80 bg-white-overlay-900 absolute inset-0 flex justify-center items-center"
						v-else
					>
						<div class="flex text-md text-gray-800 items-center gap-1.5">
							<lucide-triangle-alert class="h-5 w-5 text-amber-600" />
							To view or search SQL queries, choose a time range of less than 6
							hours
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Overlay to hide controls while building timeline -->
		<div
			class="z-1000 bg-white-overlay-800 absolute inset-0 flex justify-center items-center"
			v-if="binlog_index_state_loaded && this.$resources?.timeline?.loading"
		>
			<div class="flex gap-2 text-base text-gray-800">
				<Spinner class="w-4" />
				Building timeline...
			</div>
		</div>

		<div
			class="z-2000 bg-white absolute inset-0 flex justify-center items-center"
			v-if="binlog_index_state_loaded && binlog_indexer_running"
		>
			<div class="flex flex-col items-center gap-3 text-center px-6 max-w-lg">
				<lucide-construction class="h-8 w-8 text-gray-800 mb-1" />
				<h2 class="text-xl font-semibold text-gray-900">
					Binlog Browser Temporarily Unavailable
				</h2>
				<p class="text-gray-600">
					We are indexing new binlogs. This can take up to
					<strong>5 minutes</strong>.
					<br />
					You can wait or come back later.
				</p>
			</div>
		</div>

		<div
			class="z-3000 bg-white absolute inset-0 flex justify-center items-center"
			v-if="binlog_index_state_loaded && !binlog_indexer_enabled"
		>
			<div class="flex flex-col items-center gap-3 text-center px-6 max-w-lg">
				<lucide-construction class="h-8 w-8 text-gray-800 mb-1" />
				<h2
					class="text-xl font-semibold text-gray-900"
					v-if="
						site_hosted_on_shared_server || database_server_memory < 8 * 1024
					"
				>
					Binlog Browser Not Available
				</h2>
				<h2 class="text-xl font-semibold text-gray-900" v-else>
					Binlog Indexing Disabled
				</h2>
				<p class="text-gray-600" v-if="site_hosted_on_shared_server">
					Binlog Browser is only available for sites on dedicated servers.
					<br />
					This site is currently on shared hosting.
				</p>
				<p class="text-gray-600" v-else-if="database_server_memory < 8 * 1024">
					<span
						>This feature requires at least <strong>8 GB RAM</strong> on the db
						server.</span
					>
					<br />
					Currently, the server has only
					<strong>{{ Math.round(database_server_memory / 1024) }} GB RAM</strong
					>.
				</p>
				<p class="text-gray-600" v-else>
					Follow the
					<a
						href="https://docs.frappe.io/cloud/database-server-actions#enable--disable-binlog-indexer"
						class="text-blue-600 underline"
						target="_blank"
						rel="noopener noreferrer"
					>
						documentation
					</a>
					to enable Binlog Indexing.
				</p>
			</div>
		</div>

		<!-- Binlog Index Status Dialog -->
		<BinlogBrowserIndexStatusDialog
			v-if="isBinlogIndexerAvailable"
			:server="this.$resources?.site?.data?.server"
			:database_server="database_server"
			v-model="show_binlog_index_status_dialog"
		/>
	</div>
</template>
<script>
import BinlogBrowserChart from '../../../components/devtools/database/BinlogBrowserChart.vue';
import Header from '../../../components/Header.vue';
import {
	Tabs,
	Breadcrumbs,
	Select,
	FeatherIcon,
	Spinner,
	TextInput,
} from 'frappe-ui';
import DateTimePicker from './extras/DateTimePicker.vue';
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
		DateTimePicker,
		BinlogBrowserChart,
		Spinner,
		TextInput,
	},
	data() {
		return {
			site: null,
			errorMessage: null,
			data: null,
			start: null,
			end: null,
			type: '',
			tableName: '',
			searchString: '',
			queryIds: [],
			result: [],
			searchResultReady: false,
			showTypeColumn: false,
			showTableColumn: false,
			dateRangeValue: null,
			lastPushedState: null, // Track last pushed URL state
			binlog_index_state_loaded: false,
			binlog_indexer_enabled: false,
			binlog_indexer_running: false,
			site_hosted_on_shared_server: false,
			database_server_memory: 0,
			database_server: null,
			binlog_status_check_interval_ref: null,
			timer: null,
			event_size_comparator: '',
			event_size: null,
			show_binlog_index_status_dialog: false,
		};
	},
	mounted() {
		this.loadFromURLParams();

		// Listen for browser back/forward button
		window.addEventListener('popstate', this.handlePopState);
	},
	beforeUnmount() {
		// Clean up event listener
		window.removeEventListener('popstate', this.handlePopState);
	},
	watch: {
		site(site_name) {
			if (!site_name) return;
			// set site to query param ?site=site_name
			this.updateURLParams();

			// reset state
			this.data = null;
			this.errorMessage = null;
			this.binlog_index_state_loaded = false;
			this.binlog_indexer_enabled = false;
			this.binlog_indexer_running = false;
			this.site_hosted_on_shared_server = false;
			this.database_server_memory = 0;

			this.$resources.site.submit();
		},
		tableName() {
			this.refreshDataWithDebounce();
		},
		type() {
			this.refreshDataWithDebounce();
		},
		start() {
			this.refreshDataWithDebounce();
		},
		end() {
			this.refreshDataWithDebounce();
		},
		event_size_comparator(newVal) {
			if (newVal && this.event_size) {
				this.refreshDataWithDebounce();
			}

			if (newVal === '') {
				this.event_size = 0;
				this.refreshDataWithDebounce();
			}
		},
		event_size(newVal) {
			if (newVal && this.event_size_comparator) {
				this.refreshDataWithDebounce();
			}
		},
		isBinlogIndexerAvailable(newVal) {
			if (!newVal) return;
			this.refreshDataWithDebounce();
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
				onSuccess: (data) => {
					if (data) {
						this.fetchBinlogServiceStatus();
					}
				},
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
		binlogIndexingServiceStatus() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'binlog_indexing_service_status',
						args: {},
					};
				},
				onSuccess: (data) => {
					if (data?.message) {
						this.binlog_index_state_loaded = true;
						this.binlog_indexer_enabled = data.message?.enabled;
						this.binlog_indexer_running = data.message?.indexer_running;
						this.site_hosted_on_shared_server =
							data.message?.hosted_on_shared_server;
						this.database_server = data.message?.database_server;
						this.database_server_memory = data.message?.database_server_memory;
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
		loadFromURLParams() {
			const url = new URL(window.location.href);
			const site_name = url.searchParams.get('site');
			const startParam = url.searchParams.get('start');
			const endParam = url.searchParams.get('end');

			// Load from query params if available
			if (startParam && endParam) {
				const startDate = new Date(parseInt(startParam) * 1000);
				const endDate = new Date(parseInt(endParam) * 1000);
				this.start = startDate.toLocaleString();
				this.end = endDate.toLocaleString();
			} else {
				// Default to last 24 hours
				const now = new Date();
				this.end = now.toLocaleString();
				const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
				this.start = oneDayAgo.toLocaleString();
			}

			if (url.searchParams.get('type')) {
				this.type = url.searchParams.get('type');
			}

			if (url.searchParams.get('table')) {
				this.tableName = url.searchParams.get('table');
			}

			if (url.searchParams.get('event_size_comparator')) {
				this.event_size_comparator = url.searchParams.get(
					'event_size_comparator',
				);
			}

			if (url.searchParams.get('event_size')) {
				this.event_size = parseInt(url.searchParams.get('event_size'));
			}

			if (site_name) {
				this.site = site_name;
			}

			// Initialize lastPushedState with current URL
			this.lastPushedState = window.location.href;
		},
		handlePopState() {
			// When user clicks back/forward, reload from URL without triggering watchers
			const url = new URL(window.location.href);
			const site_name = url.searchParams.get('site');
			const startParam = url.searchParams.get('start');
			const endParam = url.searchParams.get('end');

			if (startParam && endParam) {
				const startDate = new Date(parseInt(startParam) * 1000);
				const endDate = new Date(parseInt(endParam) * 1000);
				this.start = startDate.toLocaleString();
				this.end = endDate.toLocaleString();
			}

			if (site_name) {
				this.site = site_name;
			}
		},
		updateURLParams() {
			const url = new URL(window.location.href);

			if (this.site) {
				url.searchParams.set('site', this.site);
			}

			if (this.start && this.end) {
				const startTimestamp = parseInt(new Date(this.start).getTime() / 1000);
				const endTimestamp = parseInt(new Date(this.end).getTime() / 1000);
				url.searchParams.set('start', startTimestamp);
				url.searchParams.set('end', endTimestamp);
			}

			if (this.type) {
				url.searchParams.set('type', this.type);
			} else {
				url.searchParams.delete('type');
			}

			if (this.tableName) {
				url.searchParams.set('table', this.tableName);
			} else {
				url.searchParams.delete('table');
			}

			if (this.event_size_comparator && this.event_size) {
				url.searchParams.set(
					'event_size_comparator',
					this.event_size_comparator,
				);
				url.searchParams.set('event_size', this.event_size);
			} else {
				url.searchParams.delete('event_size_comparator');
				url.searchParams.delete('event_size');
			}

			// Only push state if it's different from the last pushed state
			const newState = url.toString();
			if (this.lastPushedState !== newState) {
				window.history.pushState({}, '', url);
				this.lastPushedState = newState;
			}
		},
		fetchBinlogTimeline() {
			if (!this.start || !this.end || !this.site) return;
			if (this.$resources.timeline?.loading ?? true) return;
			if (!this.binlog_indexer_enabled) return;
			if (this.binlog_indexer_running) return;

			this.$resources.timeline.submit({
				dt: 'Site',
				dn: this.site,
				method: 'fetch_binlog_timeline',
				args: {
					start: parseInt(new Date(this.start).getTime() / 1000),
					end: parseInt(new Date(this.end).getTime() / 1000),
					query_type: this.type === 'ALL' || !this.type ? null : this.type,
					table: !this.tableName ? null : this.tableName,
					event_size_comparator: !this.event_size_comparator
						? null
						: this.event_size_comparator,
					event_size: !this.event_size_comparator ? null : this.event_size,
				},
			});
		},
		searchBinlogs() {
			if (this.$resources.searchBinlogs?.loading ?? true) return;
			if (!this.binlog_indexer_enabled) return;
			if (this.binlog_indexer_running) return;
			this.$resources.searchBinlogs.submit({
				dt: 'Site',
				dn: this.site,
				method: 'search_binlogs',
				args: {
					start: parseInt(new Date(this.start).getTime() / 1000),
					end: parseInt(new Date(this.end).getTime() / 1000),
					query_type: this.type === 'ALL' || !this.type ? null : this.type,
					table: !this.tableName ? null : this.tableName,
					search_string: this.searchString,
					event_size_comparator: !this.event_size_comparator
						? null
						: this.event_size_comparator,
					event_size: !this.event_size_comparator ? null : this.event_size,
				},
			});
		},
		fetchQueries(start, end) {
			if (this.$resources.fetchQueriesFromBinlog?.loading ?? true) return;
			if (!this.binlog_indexer_enabled) return;
			if (this.binlog_indexer_running) return;

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
		fetchBinlogServiceStatus() {
			if (this.binlog_status_check_interval_ref) {
				clearInterval(this.binlog_status_check_interval_ref);
			}
			if (!this.site) return;
			if (this.$resources?.binlogIndexingServiceStatus?.loading ?? true) return;

			this.$resources.binlogIndexingServiceStatus.submit();
			this.binlog_status_check_interval_ref = setInterval(() => {
				this.$resources.binlogIndexingServiceStatus.submit();
			}, 5000);
		},
		onZoomEvent(start, end) {
			if (!start || !end) {
				return;
			}
			this.start = null;
			this.end = null;
			this.start = start['timestamp'].toLocaleString();
			this.end = end['timestamp'].toLocaleString();
		},
		refreshDataWithDebounce() {
			clearTimeout(this.timer);
			this.timer = setTimeout(() => {
				if (this.tableName && this.tableName.indexOf('%') === -1) {
					this.tableName = '%' + this.tableName.trim() + '%';
				}
				this.updateURLParams();
				this.fetchBinlogTimeline();
			}, 1000);
		},
		resetSearch() {
			this.queryIds = [];
			this.result = [];
			this.searchResultReady = false;
			if (this.isBinlogSearchAccessible) {
				this.searchBinlogs();
			}
		},
	},
	computed: {
		isRequiredInformationReceived() {
			if (this.$resources.site?.loading ?? true) return false;
			return true;
		},
		isBinlogIndexerAvailable() {
			return this.binlog_indexer_enabled && !this.binlog_indexer_running;
		},
		timeline() {
			return this.$resources?.timeline?.data?.message ?? {};
		},
		tables() {
			return ['All Tables', ...(this.timeline?.tables ?? [])];
		},
		barChartData() {
			if (!this.timeline?.dataset) {
				return [];
			}
			// Convert the timestamp to Date
			const convertedDataset = this.timeline.dataset.map((entry) => {
				const date = new Date(entry.timestamp * 1000);
				return {
					...entry,
					timestamp: date,
				};
			});

			return convertedDataset;
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
		isBinlogSearchAccessible() {
			if (!this.site || !this.start || !this.end) {
				return false;
			}
			// Ensure the selected time range is <= 6 hours
			const startTime = new Date(this.start).getTime();
			const endTime = new Date(this.end).getTime();
			const sixHoursInMs = 6 * 60 * 60 * 1000;
			return endTime - startTime <= sixHoursInMs;
		},
		isProcessingQueries() {
			return (
				this.$resources?.timeline?.loading ||
				this.$resources?.searchBinlogs?.loading ||
				this.$resources?.fetchQueriesFromBinlog?.loading
			);
		},
	},
};
</script>
