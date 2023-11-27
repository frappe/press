<template>
	<div
		class="flex text-gray-900"
		:class="{
			'justify-end': column.align === 'right',
			'justify-center': column.align === 'center'
		}"
	>
		<div v-if="column.prefix" class="mr-2">
			<component :is="column.prefix(row)" />
		</div>
		<template v-if="column.type === 'Badge'">
			<Badge :label="formattedValue" />
			<template v-if="column.help === formattedValue">
				<Tooltip
					class="ml-2 flex cursor-pointer items-center rounded-full bg-gray-100 p-1"
					text="What's this?"
					placement="top"
				>
					<a
						href="https://frappecloud.com/docs/faq/custom_apps#why-does-it-show-attention-required-next-to-my-custom-app"
						target="_blank"
					>
						<FeatherIcon
							class="h-[13px] w-[13px] text-gray-800"
							name="help-circle"
						/>
					</a>
				</Tooltip>
			</template>
		</template>
		<template v-else-if="column.type === 'Icon'">
			<FeatherIcon v-if="icon" class="h-4 w-4" :name="icon" />
		</template>
		<Button v-else-if="column.type === 'Button'" v-bind="column.Button(row)" />
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
		<div v-else class="truncate text-base" :class="column.class">
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
