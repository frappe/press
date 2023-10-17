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
				<Button
					@click="$resources.list.reload()"
					:loading="$resources.list.list.loading"
				>
					<template #prefix>
						<i-lucide-refresh-ccw class="h-4 w-4" />
					</template>
					Refresh
				</Button>
				<Button>
					<template #prefix>
						<i-lucide-list-filter class="h-4 w-4" />
					</template>
					Filter
				</Button>
				<Dropdown
					:options="[{ label: 'Actions', onClick: () => {} }]"
					:button="{ icon: 'more-horizontal' }"
				/>
				<Button variant="solid">
					<template #prefix>
						<i-lucide-plus class="h-4 w-4" />
					</template>
					Create
				</Button>
			</div>
		</div>
		<div class="min-h-0 flex-1 overflow-y-auto">
			<ListView :columns="_columns" :rows="rows" row-key="id">
				<ListHeader>
					<ListHeaderItem
						v-for="column in _columns"
						:key="column.key"
						:column="column"
					>
						<template #prefix="{ column }">
							<FeatherIcon
								v-if="column.icon"
								:name="column.icon"
								class="h-4 w-4"
							/>
						</template>
					</ListHeaderItem>
				</ListHeader>
				<ListRows>
					<ListRow v-for="(row, i) in rows" :row="row" :idx="i" :key="row.id">
						<template #default="{ column, item }">
							<ObjectListCell :row="row" :column="column" :idx="i" />
						</template>
					</ListRow>
				</ListRows>
			</ListView>
			<div class="px-5" v-if="rows.length === 0">
				<div class="text-center text-sm leading-10 text-gray-500">
					No results found
				</div>
			</div>
			<div class="px-2 py-2 text-right">
				<Button
					@click="$resources.list.next()"
					v-if="$resources.list.hasNextPage"
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
	FeatherIcon
} from 'frappe-ui';

export default {
	name: 'List',
	props: ['list'],
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
				cache: ['ObjectList', this.list.doctype || this.list.url],
				url: this.list.url || null,
				doctype: this.list.doctype,
				fields: [
					'name',
					...(this.list.fields || []),
					...this.list.columns.map(column => column.fieldname)
				],
				filters: this.list.filters || {},
				orderBy: this.list.orderBy,
				auto: true
			};
		}
	},
	computed: {
		_columns() {
			return (this.list.columns || []).map(column => {
				return {
					...column,
					label: column.label,
					key: column.fieldname
				};
			});
		},
		rows() {
			let data = this.$resources.list.data || [];
			return data.map(row => {
				return {
					id: row.name,
					row: row,
					route: this.list.route ? this.list.route(row) : null
				};
			});
		}
	}
};
</script>
