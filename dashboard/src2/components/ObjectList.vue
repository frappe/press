<template>
	<div>
		<div class="flex items-center justify-between">
			<slot name="header-left" v-bind="context">
				<TextInput
					placeholder="Search"
					class="w-[20rem]"
					:debounce="500"
					v-model="searchQuery"
				>
					<template #prefix>
						<i-lucide-search class="h-4 w-4 text-gray-500" />
					</template>
					<template #suffix>
						<span class="text-sm text-gray-500" v-if="searchQuery">
							{{
								filteredRows.length === 0
									? 'No results'
									: `${filteredRows.length} of ${rows.length}`
							}}
						</span>
					</template>
				</TextInput>
			</slot>
			<div class="ml-2 flex shrink-0 items-center space-x-2">
				<slot name="header-right" v-bind="context" />
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
						: null
				}"
				row-key="name"
			>
				<ListHeader>
					<ListHeaderItem
						class="whitespace-nowrap"
						v-for="column in columns"
						:key="column.key"
						:item="column"
					>
						<template #prefix>
							<FeatherIcon
								v-if="column.icon"
								:name="column.icon"
								class="h-4 w-4"
							/>
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow v-for="(row, i) in filteredRows" :row="row" :key="row.name">
						<template v-slot="{ column, item }">
							<ObjectListCell
								:row="row"
								:column="column"
								:idx="i"
								:context="context"
							/>
						</template>
					</ListRow>
				</ListRows>
			</ListView>
			<div class="px-5" v-if="filteredRows.length === 0">
				<div
					class="text-center text-sm leading-10 text-gray-500"
					v-if="isLoading"
				>
					Loading...
				</div>
				<div v-else-if="$list.list?.error" class="py-4 text-center">
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
import ActionButton from './ActionButton.vue';
import ObjectListCell from './ObjectListCell.vue';
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
	mounted() {
		if (this.options.data) return;
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
			return this.$resources.list || this.options.list;
		},
		columns() {
			let columns = [];
			for (let column of this.options.columns || []) {
				columns.push({
					...column,
					label: column.label,
					key: column.fieldname
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
			if (!this.searchQuery) return this.rows;
			let query = this.searchQuery.toLowerCase();

			return this.rows.filter(row => {
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
			return this.$list.list?.loading || this.$list.loading;
		}
	}
};
</script>
