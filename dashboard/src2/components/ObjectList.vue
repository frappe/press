<template>
	<div>
		<div class="flex">
			<div>
				<TextInput placeholder="Search" class="w-[20rem]" v-model="searchQuery">
					<template #prefix>
						<i-lucide-search class="h-4 w-4 text-gray-500" />
					</template>
				</TextInput>
			</div>
			<div class="ml-auto flex items-center space-x-2">
				<Button @click="list.reload()" :loading="isLoading">
					<template #prefix>
						<i-lucide-refresh-ccw class="h-4 w-4" />
					</template>
					Refresh
				</Button>
				<Button v-if="primaryAction" v-bind="primaryAction.props">
					<template v-if="primaryAction.icon" #prefix>
						<FeatherIcon :name="primaryAction.icon" class="h-4 w-4" />
					</template>
				</Button>
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
							<ObjectListCell :row="row" :column="column" :idx="i" />
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
				<Button @click="list.next()" v-if="list.next && list.hasNextPage">
					Load more
				</Button>
			</div>
		</div>
		<component v-for="component in components" :is="component" />
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
import { isVNode } from 'vue';

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
			searchQuery: '',
			filteredRows: [],
			components: []
		};
	},
	watch: {
		searchQuery: {
			immediate: true,
			handler: debounce(function (query) {
				if (!query) {
					this.filteredRows = this.rows;
					return;
				}
				this.filteredRows = this.rows.filter(row => {
					let values = this.options.columns.map(column => {
						let value = row[column.fieldname];
						if (column.format) {
							value = column.format(value, row);
						}
						return value;
					});
					for (let value of values) {
						if (value && value.toLowerCase().includes(query.toLowerCase())) {
							return true;
						}
					}
					return false;
				});
			}, 300)
		}
	},
	resources: {
		list() {
			if (this.options.resource) {
				return this.options.resource(this.context);
			}
			return {
				type: 'list',
				cache: ['ObjectList', this.options.doctype || this.options.url],
				url: this.options.url || null,
				doctype: this.options.doctype,
				fields: [
					'name',
					...(this.options.fields || []),
					...this.options.columns.map(column => column.fieldname)
				],
				filters: this.options.filters || {},
				orderBy: this.options.orderBy,
				auto: true,
				onData: () => {
					this.filteredRows = this.rows;
				},
				onSuccess: () => {
					this.filteredRows = this.rows;
				}
			};
		}
	},
	computed: {
		list() {
			return this.$resources.list;
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
		primaryAction() {
			if (!this.options.primaryAction) return null;
			let props = this.options.primaryAction(this.context);
			let { icon, ...rest } = props;
			return {
				icon,
				props: {
					variant: 'solid',
					...rest,
					onClick: () => {
						if (props.onClick) {
							let result = props.onClick(this.context);
							if (isVNode(result)) {
								this.components.push(result);
							}
						}
					}
				}
			};
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
