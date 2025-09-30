<template>
	<Popover class="w-full">
		<template #target="{ togglePopover }">
			<Button
				class="font-mono text-xs"
				:label="modelValue?.label || 'Select'"
				icon-right="chevron-down"
				@click="togglePopover"
			/>
		</template>
		<template #body="{ isOpen, togglePopover }">
			<div
				v-show="isOpen"
				class="relative mt-1 rounded-lg bg-surface-modal text-base shadow-2xl"
			>
				<div class="max-h-[15rem] overflow-y-auto px-1.5 pb-1.5 pt-1.5">
					<div
						v-for="option in options"
						:key="option.value"
						@click="selectOption(option, togglePopover)"
						class="flex cursor-pointer items-center justify-between rounded px-2.5 py-1.5 text-base hover:bg-gray-50"
						:class="{ 'bg-surface-gray-3': isSelected(option) }"
					>
						<div class="flex flex-1 gap-2 overflow-hidden items-center">
							<div class="flex flex-shrink-0">
								<svg
									v-if="isSelected(option)"
									class="h-4 w-4 text-ink-gray-7"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									></path>
								</svg>
								<div v-else class="h-4 w-4" />
							</div>
							<span class="flex-1 truncate text-ink-gray-7">
								{{ option.label }}
							</span>
						</div>
					</div>
					<div
						v-if="options.length === 0"
						class="rounded-md px-2.5 py-1.5 text-base text-ink-gray-5"
					>
						No results found
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script>
import { Popover, Button } from 'frappe-ui';

export default {
	name: 'CommitChooser',
	components: {
		Popover,
		Button,
	},
	props: ['options', 'modelValue'],
	emits: ['update:modelValue'],
	methods: {
		selectOption(option, togglePopover) {
			this.$emit('update:modelValue', {
				label: this.isVersion(option.label)
					? option.label
					: option.label.match(/\((\w+)\)$/)?.[1] || option.label,
				value: option.value,
			});
			togglePopover();
		},
		isSelected(option) {
			return this.modelValue?.value === option.value;
		},
		isVersion(tag) {
			return tag.match(/^v\d+\.\d+\.\d+$/);
		},
	},
};
</script>
