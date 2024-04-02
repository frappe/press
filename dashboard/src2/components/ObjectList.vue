<template>
	<div>
		<div v-if="hideControls" class="flex items-center justify-between">
			<slot name="header-left" v-bind="context">
				<div class="flex items-center space-x-2">
					<TextInput
						placeholder="Search"
						class="max-w-[20rem]"
						:debounce="500"
						v-model="searchQuery"
					>
						<template #prefix>
							<i-lucide-search class="h-4 w-4 text-gray-500" />
						</template>
						<template #suffix>
							<span class="text-sm text-gray-500" v-if="searchQuery">
								{{ searchQuerySummary }}
							</span>
						</template>
					</TextInput>
					<ObjectListFilters
						v-if="filterControls.length"
						:filterControls="filterControls"
						@update:filter="onFilterControlChange"
					/>
				</div>
			</slot>
			<div class="ml-2 flex shrink-0 items-center space-x-2">
				<slot name="header-right" v-bind="context" />
				<Tooltip
					v-if="options.experimental"
					text="This is an experimental feature"
				>
					<div class="rounded-md bg-purple-100 p-1.5">
						<i-lucide-flask-conical class="h-4 w-4 text-purple-500" />
					</div>
				</Tooltip>
				<Tooltip v-if="options.documentation" text="View documentation">
					<div class="rounded-md bg-gray-100 p-1.5">
						<a :href="options.documentation" target="_blank">
							<FeatherIcon class="h-4 w-4" name="help-circle" />
						</a>
					</div>
				</Tooltip>
				<Tooltip text="Refresh" v-if="$list">
					<Button label="Refresh" @click="$list.reload()" :loading="isLoading">
						<template #icon>
							<FeatherIcon class="h-4 w-4" name="refresh-ccw" />
						</template>
					</Button>
				</Tooltip>
				<ActionButton v-bind="secondaryAction" :context="context" />
				<ActionButton v-bind="primaryAction" :context="context" />
			</div>
		</div>
		<div class="mt-3 min-h-0 flex-1 overflow-y-auto">
			<ListView
				:columns="columns"
				:rows="filteredRows"
				:options="{
					selectable: this.options.selectable || false,
					onRowClick: this.options.onRowClick
						? row => this.options.onRowClick(row)
						: () => {},
					getRowRoute: this.options.route
						? row => this.options.route(row)
						: null,
					emptyState: {}
				}"
				row-key="name"
			>
				<template v-if="options.groupHeader" #group-header="{ group }">
					<component :is="options.groupHeader({ ...context, group })" />
				</template>
				<template #cell="{ item, row, column }">
					<ObjectListCell
						:class="[
							column == columns[0] ? ' text-gray-900' : ' text-gray-700'
						]"
						:row="row"
						:column="column"
						:context="context"
					/>
				</template>
			</ListView>
			<div class="px-5" v-if="filteredRows.length === 0">
				<div
					class="text-center text-sm leading-10 text-gray-500"
					v-if="isLoading"
				>
					Loading...
				</div>
				<div v-else-if="$list?.list?.error" class="py-4 text-center">
					<ErrorMessage :message="$list.list.error" />
				</div>
				<div v-else class="text-center text-sm leading-10 text-gray-500">
					No results found
				</div>
			</div>
			<div class="px-2 py-2 text-right" v-if="$list">
				<Button
					v-if="$list.next && $list.hasNextPage"
					@click="$list.next()"
					:loading="isLoading"
				>
					Load more
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
import { reactive } from 'vue';
import ActionButton from './ActionButton.vue';
import ObjectListCell from './ObjectListCell.vue';
import ObjectListFilters from './ObjectListFilters.vue';
import {
	Dropdown,
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	ListSelectBanner,
	TextInput,
	FeatherIcon,
	Tooltip,
	ErrorMessage
} from 'frappe-ui';

let subscribed = {};

export default {
	name: 'ObjectList',
	props: ['options'],
	components: {
		ActionButton,
		ObjectListCell,
		ObjectListFilters,
		Dropdown,
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRows,
		ListRow,
		ListRowItem,
		ListSelectBanner,
		TextInput,
		FeatherIcon,
		Tooltip,
		ErrorMessage
	},
	data() {
		return {
			lastRefreshed: null,
			searchQuery: ''
		};
	},
	watch: {
		searchQuery(value) {
			if (this.options.searchField && this.$list?.list) {
				if (value) {
					this.$list.update({
						filters: {
							...this.$list.filters,
							[this.options.searchField]: ['like', `%${value.toLowerCase()}%`]
						},
						start: 0,
						pageLength: this.options.pageLength || 20
					});
				} else {
					this.$list.update({
						filters: {
							...this.$list.filters,
							[this.options.searchField]: undefined
						},
						start: 0,
						pageLength: this.options.pageLength || 20
					});
				}
				this.$list.reload();
			}
		}
	},
	resources: {
		list() {
			if (this.options.data) return;
			if (this.options.list) return;
			if (this.options.resource) {
				return this.options.resource(this.context);
			}
			return {
				type: 'list',
				cache: [
					'ObjectList',
					this.options.doctype || this.options.url,
					this.options.filters
				],
				url: this.options.url || null,
				doctype: this.options.doctype,
				pageLength: this.options.pageLength || 20,
				fields: [
					'name',
					...(this.options.fields || []),
					...this.options.columns.map(column => column.fieldname)
				],
				filters: this.options.filters || {},
				orderBy: this.options.orderBy,
				auto: true,
				onSuccess: () => {
					this.lastRefreshed = new Date();
				},
				onError: e => {
					if (this.$list.data) {
						this.$list.data = [];
					}
				}
			};
		}
	},
	beforeUpdate() {
		if (this.$list?.list) {
			let filters = this.$list.list?.params?.filters;
			for (let control of this.filterControls) {
				if (control.value !== filters[control.fieldname]) {
					control.value = filters[control.fieldname];
				}
			}
		}
	},
	mounted() {
		if (this.options.data) return;
		if (this.options.list) {
			let resource = this.$list.list || this.$list;
			if (!resource.fetched && !resource.loading && this.$list.auto != false) {
				resource.fetch();
			}
		}
		if (this.options.doctype) {
			let doctype = this.options.doctype;
			if (subscribed[doctype]) return;
			this.$socket.emit('doctype_subscribe', doctype);
			subscribed[doctype] = true;

			this.$socket.on('list_update', data => {
				let names = (this.$list.data || []).map(d => d.name);
				if (
					data.doctype === doctype &&
					names.includes(data.name) &&
					// update list if last refreshed is more than 5 seconds ago
					new Date() - this.lastRefreshed > 5000
				) {
					this.$list.reload();
				}
			});
		}
	},
	beforeUnmount() {
		if (this.options.doctype) {
			let doctype = this.options.doctype;
			this.$socket.emit('doctype_unsubscribe', doctype);
			subscribed[doctype] = false;
		}
	},
	computed: {
		$list() {
			if (this.$resources.list) return this.$resources.list;

			if (this.options.list) {
				if (typeof this.options.list === 'function') {
					return this.options.list(this.options.context);
				}
				return this.options.list;
			}
		},
		columns() {
			let columns = [];
			for (let column of this.options.columns || []) {
				columns.push({
					...column,
					label: column.label,
					key: column.fieldname,
					align: column.align || 'left'
				});
			}
			if (this.options.rowActions) {
				columns.push({
					label: '',
					key: '__actions',
					type: 'Actions',
					width: '100px',
					align: 'right',
					actions: row => this.options.rowActions({ ...this.context, row })
				});
			}
			return columns;
		},
		rows() {
			if (this.options.data) {
				return this.options.data(this.context);
			}
			return this.$list.data || [];
		},
		filteredRows() {
			if (this.options.searchField || !this.searchQuery) return this.rows;
			let query = this.searchQuery.toLowerCase();

			return this.rows
				.map(row => {
					if (row.rows && row.group) {
						// group
						return {
							...row,
							rows: row.rows.filter(row => this.filterRow(query, row))
						};
					}
					if (this.filterRow(query, row)) {
						return row;
					}
					return false;
				})
				.filter(Boolean);
		},
		searchQuerySummary() {
			if (this.options.searchField) return;

			let summary;
			if (this.filteredRows.length === 0) {
				summary = 'No results';
			} else if (this.filteredRows[0].rows) {
				let total = this.rows.reduce(
					(acc, group) => acc + group.rows.length,
					0
				);
				let filtered = this.filteredRows.reduce(
					(acc, group) => acc + group.rows.length,
					0
				);
				summary = `${filtered} of ${total}`;
			} else {
				summary = `${this.filteredRows.length} of ${this.rows.length}`;
			}
			return summary;
		},
		filterControls() {
			if (!this.options.filterControls) return [];
			let controls = this.options.filterControls(this.context);
			return controls
				.filter(control => control.fieldname)
				.map(control => {
					return reactive({ ...control, value: control.default || undefined });
				});
		},
		primaryAction() {
			if (!this.options.primaryAction) return null;
			let props = this.options.primaryAction(this.context);
			if (!props) return null;
			return props;
		},
		secondaryAction() {
			if (!this.options.secondaryAction) return null;
			let props = this.options.secondaryAction(this.context);
			if (!props) return null;
			return props;
		},
		context() {
			return {
				...this.options.context,
				listResource: this.$list
			};
		},
		isLoading() {
			if (this.options.data) return false;
			return this.$list.list?.loading || this.$list.loading;
		},
		hideControls() {
			return !this.options.hideControls;
		}
	},
	methods: {
		filterRow(query, row) {
			let values = this.options.columns.map(column => {
				let value = row[column.fieldname];
				if (column.format) {
					value = column.format(value, row);
				}
				return value;
			});
			for (let value of values) {
				if (value && value.toLowerCase?.().includes(query)) {
					return true;
				}
			}
			return false;
		},
		onFilterControlChange(control) {
			let filters = { ...this.$list.filters };
			for (let c of this.filterControls) {
				filters[c.fieldname] = c.value;
			}
			this.$list.update({
				filters,
				start: 0,
				pageLength: this.options.pageLength || 20
			});
			this.$list.reload();
		}
	}
};
</script>
