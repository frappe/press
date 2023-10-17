<template>
	<div>
		<Badge v-if="column.type == 'Badge'" :label="formattedValue" />
		<template v-else-if="column.type === 'Icon'">
			<FeatherIcon v-if="icon" class="h-4 w-4" :name="icon" />
		</template>
		<div v-else class="truncate text-base">
			{{ formattedValue }}
		</div>
	</div>
</template>
<script>
export default {
	name: 'ObjectListCell',
	props: {
		row: Object,
		column: Object,
		idx: Number
	},
	computed: {
		value() {
			return this.row.row[this.column.key];
		},
		formattedValue() {
			let formattedValue = this.column.format
				? this.column.format(this.value, this.row.row)
				: this.value;
			if (formattedValue == null) {
				formattedValue = '';
			}
			return String(formattedValue);
		},
		icon() {
			return this.column.type === 'Icon' && this.column.Icon(this.value);
		}
	},
	methods: {}
};
</script>
