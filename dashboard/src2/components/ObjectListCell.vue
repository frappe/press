<template>
	<div
		class="flex"
		:class="{
			'justify-end': column.align === 'right',
			'justify-center': column.align === 'center'
		}"
	>
		<Badge v-if="column.type == 'Badge'" :label="formattedValue" />
		<template v-else-if="column.type === 'Icon'">
			<FeatherIcon v-if="icon" class="h-4 w-4" :name="icon" />
		</template>
		<div class="text-base text-gray-600" v-else-if="column.type == 'Timestamp'">
			<div class="flex">
				<Tooltip :text="value">
					{{ value ? $dayjs(value).fromNow() : '' }}
				</Tooltip>
			</div>
		</div>
		<div v-else-if="column.type == 'Actions'">
			<Dropdown v-if="actions?.length" :options="actions">
				<button
					class="flex items-center rounded bg-gray-100 px-1 py-0.5 hover:bg-gray-200"
				>
					<FeatherIcon name="more-horizontal" class="h-4 w-4" />
				</button>
			</Dropdown>
		</div>
		<div v-else class="truncate text-base">
			{{ formattedValue }}
		</div>
	</div>
</template>
<script>
import { Tooltip } from 'frappe-ui';

export default {
	name: 'ObjectListCell',
	props: {
		row: Object,
		column: Object,
		idx: Number
	},
	computed: {
		value() {
			return this.row[this.column.key];
		},
		formattedValue() {
			let formattedValue = this.column.format
				? this.column.format(this.value, this.row)
				: this.value;
			if (formattedValue == null) {
				formattedValue = '';
			}
			return String(formattedValue);
		},
		icon() {
			return this.column.type === 'Icon' && this.column.Icon(this.value);
		},
		actions() {
			if (!this.column.type === 'Actions') return;
			let actions = this.column.actions(this.row);
			return actions;
		}
	},
	components: { Tooltip }
};
</script>
