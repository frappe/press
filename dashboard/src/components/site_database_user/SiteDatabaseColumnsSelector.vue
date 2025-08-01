<template>
	<FPopover ref="rootRef" class="w-full">
		<template #target="{ togglePopover }" class="w-full">
			<Button @click="togglePopover()" class="px-4">
				{{
					columns.length == 0
						? 'All Columns Allowed'
						: `${columns.length} Columns Selected`
				}}
			</Button>
		</template>
		<template #body="{ isOpen, togglePopover }" class="w-full">
			<div
				v-show="isOpen"
				class="bg-surface-white bg absolute right-0 z-[999] mt-1.5 flex max-h-[15rem] w-full list-none flex-col gap-2 overflow-y-auto overflow-x-hidden rounded-lg bg-white p-0 px-1.5 py-1.5 shadow-2xl"
			>
				<FormControl
					theme="outline"
					placeholder="Search"
					v-model="searchQuery"
				/>

				<FCheckbox
					class="cursor-pointer"
					size="sm"
					v-for="column in filteredColumns"
					:modelValue="isChecked(column)"
					@change="(e) => toggleSelection(column, e)"
					:label="column"
				/>
			</div>
		</template>
	</FPopover>
</template>
<script>
import { Popover, Checkbox } from 'frappe-ui';

export default {
	name: 'SiteDatabaseColumnsSelector',
	props: ['modelValue', 'availableColumns'],
	emits: ['update:modelValue'],
	components: {
		FPopover: Popover,
		FCheckbox: Checkbox,
	},
	data() {
		return {
			searchQuery: '',
		};
	},
	mounted() {
		this.searchQuery = '';
	},
	computed: {
		columns() {
			return this.modelValue;
		},
		allAvailableColumns() {
			return this.availableColumns
				.reduce(
					(acc, item) => {
						return acc.includes(item) ? acc : [...acc, item];
					},
					[...this.modelValue],
				)
				.sort();
		},
		filteredColumns() {
			return this.allAvailableColumns.filter((column) =>
				column.toLowerCase().includes(this.searchQuery.toLowerCase()),
			);
		},
	},
	methods: {
		isChecked(column) {
			return this.columns.includes(column);
		},
		toggleSelection(column, event) {
			event.preventDefault();
			event.stopPropagation();
			if (this.isChecked(column)) {
				this.$emit(
					'update:modelValue',
					this.columns.filter((c) => c != column),
				);
			} else {
				this.$emit('update:modelValue', [...this.columns, column]);
			}
		},
	},
};
</script>
