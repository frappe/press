<template>
	<div>
		<div class="flex px-5 pt-5">
			<div>
				<TextInput placeholder="Search" class="w-[20rem]">
					<template #prefix>
						<i-lucide-search class="h-4 w-4 text-gray-500" />
					</template>
				</TextInput>
			</div>
			<div class="ml-auto flex items-center space-x-2">
				<Button @click="list.reload()" :loading="list.list.loading">
					<template #prefix>
						<i-lucide-refresh-ccw class="h-4 w-4" />
					</template>
					Refresh
				</Button>
				<!-- <Dropdown
					:options="[{ label: 'Actions', onClick: () => {} }]"
					:button="{ icon: 'more-horizontal' }"
				/> -->
				<Button v-if="primaryAction" v-bind="primaryAction">
					<template v-if="primaryAction.icon" #prefix>
						<FeatherIcon :name="primaryAction.icon" class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>
		<div class="mt-3 min-h-0 flex-1 overflow-y-auto px-5">
			<ListView
				:columns="columns"
				:rows="rows"
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
					<ListRow v-for="(row, i) in rows" :row="row" :key="row.name">
						<template v-slot="{ column, item }">
							<ObjectListCell :row="row" :column="column" :idx="i" />
						</template>
					</ListRow>
				</ListRows>
			</ListView>
			<div class="px-5" v-if="rows.length === 0">
				<div
					class="text-center text-sm leading-10 text-gray-500"
					v-if="list.list.loading"
				>
					Loading...
				</div>
				<div v-else class="text-center text-sm leading-10 text-gray-500">
					No results found
				</div>
			</div>
			<div class="px-2 py-2 text-right">
				<Button @click="list.next()" v-if="list.hasNextPage">
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
	FeatherIcon
} from 'frappe-ui';

export default {
	name: 'List',
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
	resources: {
		list() {
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
				auto: true
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
					actions: this.options.rowActions
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
			return {
				variant: 'solid',
				...props
			};
		},
		context() {
			return {
				...this.options.context,
				listResource: this.list
			};
		}
	}
};
</script>
