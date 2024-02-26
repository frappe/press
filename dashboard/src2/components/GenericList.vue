<template>
	<ListView
		:columns="columns"
		:rows="rows"
		:options="{
			selectable: options.selectable || false,
			onRowClick: row => (options.onRowClick ? options.onRowClick(row) : {}),
			getRowRoute: options.route ? getRowRoute : null
		}"
		row-key="name"
		@update:selections="e => this.$emit('update:selections', e)"
	>
		<ListHeader>
			<template v-for="column in columns" :key="column.field">
				<ListHeaderItem :item="column">
					<template #prefix>
						<FeatherIcon
							v-if="column.icon"
							:name="column.icon"
							class="h-4 w-4"
						/>
					</template>
				</ListHeaderItem>
			</template>
		</ListHeader>
		<ListRows>
			<div
				v-if="rows.length === 0"
				class="text-center text-sm leading-10 text-gray-500"
			>
				No results found
			</div>
			<ListRow v-for="(row, i) in rows" :row="row" :key="row.name">
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
</template>

<script>
import {
	ListHeader,
	ListView,
	ListHeaderItem,
	ListRow,
	ListSelectBanner
} from 'frappe-ui';
import ObjectListCell from './ObjectListCell.vue';

export default {
	name: 'GenericList',
	components: {
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRow,
		ListSelectBanner,
		ObjectListCell
	},
	props: ['options'],
	emits: ['update:selections'],
	computed: {
		columns() {
			if (!this.options.columns && this.options.data.length > 0) {
				console.log(Object.keys(this.options.data[0]));
				return Object.keys(this.options.data[0]).map(fieldname => {
					return {
						fieldname,
						key: fieldname,
						label: fieldname
					};
				});
			}
			return this.options.columns
				.filter(column => {
					if (column.condition) {
						return column.condition(this.context);
					}
					return true;
				})
				.map(column => {
					if (!column.key) {
						column.key = column.fieldname;
					}
					return column;
				});
		},
		rows() {
			return this.options.data;
		},
		context() {
			return this.options.context;
		}
	},
	methods: {
		getRowRoute(row) {
			if (this.options.route) {
				let route = this.options.route(row);
				return route || this.$route;
			}
			return null;
		},
		formattedValue(value, column, row) {
			let formattedValue =
				column.format && value ? column.format(value, row) : value;
			if (!formattedValue) {
				formattedValue = '';
			}
			return String(formattedValue);
		}
	}
};
</script>
