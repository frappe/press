<template>
	<component
		:is="column.link ? 'a' : 'div'"
		:href="column.link ? column.link(value, row) : undefined"
		:target="column.link ? '_blank' : undefined"
		class="flex items-center"
		:class="{
			'text-gray-900 outline-gray-400 hover:text-gray-700': column.link,
			'justify-end': column.align === 'right',
			'justify-center': column.align === 'center',
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
			<select
				class="inline-flex items-center justify-center gap-2 transition-colors focus:outline-none shrink-0 text-ink-gray-8 border border-outline-gray-2 hover:border-outline-gray-3 active:border-outline-gray-3 active:bg-surface-gray-4 focus-visible:ring focus-visible:ring-outline-gray-3 h-7 p-0 pl-2 pr-8 w-48 text-base rounded"
				@change="fireOnClick({ value: $event.target.value })"
			>
				<option v-for="opt in formattedValue" :value="opt.value">
					{{ opt.title ?? opt.value }}
				</option>
			</select>
		</div>
		<div class="text-base text-gray-600" v-else-if="column.type == 'Timestamp'">
			<div class="flex">
				<Tooltip :text="$format.date(value)">
					{{ value ? $dayjs(value).fromNow() : '' }}
				</Tooltip>
			</div>
		</div>
		<div class="text-base" v-else-if="column.type == 'Date'">
			{{ formattedDate }}
		</div>
		<div v-else-if="column.type == 'Actions'">
			<Dropdown v-if="showDropdown" :options="actions" @click.stop>
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
		context: Object,
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
		formattedDate() {
			if (!this.value) return '';
			if (this.value.includes(' ')) {
				return this.$format.date(this.value, 'lll');
			}
			return this.$format.date(this.value, 'll');
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
				row: this.row,
			};
		},
		showDropdown() {
			let filteredOptions = (this.actions || [])
				.filter(Boolean)
				.filter((option) => (option.condition ? option.condition() : true));

			return filteredOptions.length > 0;
		},
	},
	components: { Tooltip, ActionButton },
	methods: {
		fireOnClick({ value }) {
			this.formattedValue.find((obj) => obj?.value === value)?.onClick?.();
		},
	},
};
</script>
