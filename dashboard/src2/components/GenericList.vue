<template>
	<ListView
		:columns="columns"
		:rows="rows"
		:options="{
			selectable: options.selectable || false,
			onRowClick: () => {},
			getRowRoute: options.route ? row => options.route(row) : null
		}"
		row-key="name"
		@update:selections="e => this.$emit('update:selections', e)"
	>
		<ListHeader>
			<template v-for="column in columns" :key="column.field">
				<ListHeaderItem
					v-if="column.condition ? column.condition() : true"
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
			</template>
		</ListHeader>
		<ListRows>
			<ListRow v-for="(row, i) in rows" :row="row" :key="row.name">
				<template v-slot="{ column, item }">
					<div v-if="column.condition ? column.condition() : true">
						<Badge
							v-if="column.type === 'Badge'"
							:label="formattedValue(row[column.field], column, row)"
						/>
						<component
							v-else-if="column.type === 'component' && column.component"
							:is="column.component(row)"
						/>
						<div v-else class="truncate text-base" :class="column.class">
							{{ formattedValue(row[column.field], column, row) }}
						</div>
					</div>
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
import CommitChooser from '@/components/utils/CommitChooser.vue';

export default {
	name: 'GenericList',
	components: {
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRow,
		ListSelectBanner,
		CommitChooser
	},
	props: ['options'],
	emits: ['update:selections'],
	computed: {
		columns() {
			return this.options.columns;
		},
		rows() {
			return this.options.data;
		},
		context() {
			return this.options.context;
		}
	},
	methods: {
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
