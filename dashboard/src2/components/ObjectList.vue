<template>
	<div>
		<div class="flex">
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
			<div class="ml-auto flex items-center space-x-2">
				<slot name="header-right" v-bind="context" />
				<Button label="Refresh" @click="list.reload()" :loading="isLoading">
					<template #icon>
						<FeatherIcon class="h-4 w-4" name="refresh-ccw" />
					</template>
				</Button>
				<ActionButton v-bind="primaryAction" :context="context" />
			</div>
		</div>
		<div class="mt-3 min-h-0 flex-1 overflow-y-auto">
			<ListView
				:columns="columns"
				:rows="filteredRows"
				:options="{
					selectable: this.options.selectable || false,
					onRowClick: () => {},
					getRowRoute: this.options.route
						? row => this.options.route(row)
						: null
				}"
				row-key="name"
			>
				<ListHeader>
					<ListHeaderItem
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
				<div v-else class="text-center text-sm leading-10 text-gray-500">
					No results found
				</div>
			</div>
			<div class="px-2 py-2 text-right">
				<Button
					@click="list.next()"
					v-if="list.next && list.hasNextPage"
					:loading="list.list.loading"
				>
					Load more
				</Button>
			</div>
		</div>
	</div>
</template>
<script>
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
	debounce
} from 'frappe-ui';
import { onDocUpdate } from 'frappe-ui/src/resources/realtime';

export default {
	name: 'ObjectList',
	props: ['options'],
	components: {
		Dropdown,
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRows,
		ListRow,
		ListRowItem,
		ListSelectBanner,
		TextInput,
		FeatherIcon
	},
	data() {
		return {
			searchQuery: ''
		};
	},
	resources: {
		list() {
			if (this.options.list) return {};
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
				fields: [
					'name',
					...(this.options.fields || []),
					...this.options.columns.map(column => column.fieldname)
				],
				filters: this.options.filters || {},
				orderBy: this.options.orderBy,
				auto: true
			};
		}
	},
	mounted() {
		if (this.options.list) return {}
		onDocUpdate(this.$socket, this.list.doctype, () => {
			this.list.reload();
		});
	},
	computed: {
		list() {
			return this.options.list || this.$resources.list;
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
			let data = this.list.data || [];
			return data;
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
		context() {
			return {
				...this.options.context,
				listResource: this.list
			};
		},
		isLoading() {
			return this.list.list?.loading || this.list.loading;
		}
	}
};
</script>
