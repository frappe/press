<template>
	<component
		:is="column.link ? 'a' : 'div'"
		:href="column.link ? column.link(value, row) : undefined"
		:target="column.link ? '_blank' : undefined"
		class="flex items-center"
		:class="{
			'text-gray-900 outline-gray-400 hover:text-gray-700': column.link,
			'justify-end': column.align === 'right',
			'justify-center': column.align === 'center'
		}"
	>
		<div v-if="column.prefix" class="mr-2">
			<component :is="column.prefix(row)" />
		</div>
		<component
			v-if="column.type === 'Component'"
			:is="column.component(contextWithRow)"
		/>
		<template v-else-if="column.type === 'Badge'">
			<Badge :label="formattedValue" :theme="theme" v-if="formattedValue" />
		</template>
		<template v-else-if="column.type === 'Icon'">
			<FeatherIcon v-if="icon" class="h-4 w-4" :name="icon" />
		</template>
		<template v-else-if="column.type === 'Button'">
			<ActionButton v-if="button" v-bind="button" />
		</template>
		<div v-else-if="column.type == 'Image'">
			<img :src="value" :alt="formattedValue" class="h-6 w-6 rounded" />
		</div>
		<div v-else-if="column.type == 'Select'">
			<Dropdown :options="formattedValue" right>
				<template v-slot="{ open }">
					<Button type="white" icon-right="chevron-down">
						{{ row.selectedOption || value[0] }}
					</Button>
				</template>
			</Dropdown>
		</div>
		<div class="text-base text-gray-600" v-else-if="column.type == 'Timestamp'">
			<div class="flex">
				<Tooltip :text="$format.date(value)">
					{{ value ? $dayjs(value).fromNow() : '' }}
				</Tooltip>
			</div>
		</div>
		<div v-else-if="column.type == 'Actions'">
			<Dropdown v-if="showDropdown" :options="actions">
				<button
					class="flex items-center rounded bg-gray-100 px-1 py-0.5 hover:bg-gray-200"
				>
					<FeatherIcon name="more-horizontal" class="h-4 w-4" />
				</button>
			</Dropdown>
		</div>
		<div v-else class="truncate text-base" :class="cellClass">
			{{ formattedValue }}
		</div>
		<div v-if="column.suffix" class="ml-2">
			<component :is="column.suffix(row)" />
		</div>
	</component>
</template>
<script>
import { Tooltip } from 'frappe-ui';
import ActionButton from './ActionButton.vue';

export default {
	name: 'ObjectListCell',
	props: {
		row: Object,
		column: Object,
		idx: Number,
		context: Object
	},
	computed: {
		value() {
			return this.row[this.column.key];
		},
		theme() {
			const theme = this.column.theme;
			if (typeof theme === 'function') {
				return theme(this.value, this.row);
			}

			return theme;
		},
		formattedValue() {
			let formattedValue = this.column.format
				? this.column.format(this.value, this.row)
				: this.value;
			if (formattedValue == null) {
				formattedValue = '';
			}
			return typeof formattedValue === 'object'
				? formattedValue
				: String(formattedValue);
		},
		icon() {
			return this.column.type === 'Icon' && this.column.Icon(this.value);
		},
		actions() {
			if (!this.column.type === 'Actions') return;
			let actions = this.column.actions(this.row);
			return actions;
		},
		button() {
			if (!this.column.type === 'Button') return;
			return this.column.Button(this.contextWithRow);
		},
		cellClass() {
			if (!this.column.class) return;
			if (typeof this.column.class == 'string') return this.column.class;
			return this.column.class(this.contextWithRow);
		},
		contextWithRow() {
			return {
				...this.context,
				row: this.row
			};
		},
		showDropdown() {
			let filteredOptions = (this.actions || [])
				.filter(Boolean)
				.filter(option => (option.condition ? option.condition() : true));

			return filteredOptions.length > 0;
		}
	},
	components: { Tooltip, ActionButton }
};
</script>
