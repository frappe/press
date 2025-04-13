<template>
	<div class="relative space-y-1.5">
		<label class="block text-xs text-gray-600" v-if="label">
			{{ label }}
		</label>
		<Combobox
			:modelValue="value"
			@update:modelValue="
				val => {
					emit('update:modelValue', val?.value);
				}
			"
			v-slot="{ open }"
			:nullable="nullable"
			:multiple="multiple"
		>
			<Popover class="w-full" ref="rootRef">
				<template #target="{ togglePopover }">
					<ComboboxButton v-show="false" ref="comboboxButton"></ComboboxButton>
					<div
						class="border-outline-gray-1 bg-surface-gray-1 text-text-icons-gray-8 hover:border-outline-gray-2 hover:bg-surface-gray-1 form-input flex h-7 w-full items-center justify-between gap-2 rounded p-0 text-sm transition-colors"
					>
						<ComboboxInput
							autocomplete="off"
							@focus="
								() => {
									togglePopover();
									if (!open.value) {
										$refs.comboboxButton?.$el.click();
									}
								}
							"
							@change="handleQueryChange"
							:displayValue="getDisplayValue"
							:placeholder="!modelValue ? placeholder : null"
							class="focus:ring-outline-gray-3 h-full w-full rounded border border-gray-100 bg-gray-100 bg-transparent pl-2 pr-5 text-base text-gray-800 placeholder-gray-500 transition-colors focus:border-gray-500 focus:bg-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-gray-400"
						/>
					</div>
				</template>
				<template #body="{ isOpen, togglePopover }">
					<div v-show="isOpen">
						<ComboboxOptions
							class="bg-surface-white absolute right-0 z-[999] max-h-[15rem] w-full overflow-y-auto rounded-lg p-0 shadow-2xl"
							v-show="filteredOptions.length"
						>
							<div class="w-full list-none bg-white px-1.5 py-1.5">
								<ComboboxOption
									v-for="option in filteredOptions"
									v-slot="{ active, selected }"
									:key="option.value"
									:value="option"
									:disabled="String(option.value).startsWith('_separator')"
									:title="option.label"
									class="flex items-center"
									@click="
										() => {
											if (!open.value) {
												$refs.comboboxButton?.$el.click();
											}
										}
									"
								>
									<span
										v-if="String(option.value).startsWith('_separator')"
										class="!text-text-icons-gray-5 flex w-full items-center gap-2 px-2.5 pb-2 pt-3 text-xs font-medium"
									>
										{{ option.label }}
									</span>
									<li
										v-else
										class="flex w-full cursor-pointer select-none items-center justify-between truncate rounded px-2.5 py-1.5 text-base"
										:class="{
											'bg-gray-100': active,
											'bg-gray-300': selected
										}"
									>
										{{ option.label }}
									</li>
								</ComboboxOption>
							</div>
							<div
								class="border-outline-gray-2 bg-surface-gray-1 sticky bottom-0 rounded-b-sm border-t"
								v-if="actionButton"
							>
								<component
									:is="actionButton.component"
									v-if="actionButton?.component"
									@change="updateOptions"
								></component>
								<Button
									v-else
									:iconLeft="actionButton.icon"
									class="text-text-icons-gray-8 w-full rounded-none text-xs"
									@click="actionButton.handler"
								>
									{{ actionButton.label }}
								</Button>
							</div>
						</ComboboxOptions>
					</div>
				</template>
			</Popover>
		</Combobox>
		<div
			class="text-text-icons-gray-4 hover:text-text-icons-gray-5 absolute right-[1px] top-[3px] cursor-pointer p-1"
			@click="clearValue"
			v-show="modelValue"
		>
			<FeatherIcon name="x" class="mt-3.5 h-4 w-4 stroke-gray-700" />
		</div>
	</div>
</template>

<script setup lang="ts">
import {
	Combobox,
	ComboboxButton,
	ComboboxInput,
	ComboboxOption,
	ComboboxOptions
} from '@headlessui/vue';
import { ComputedRef, PropType, computed, ref, watch } from 'vue';
import { Popover } from 'frappe-ui';

type Option = {
	label: string;
	value: string;
};

const emit = defineEmits(['update:modelValue']);

type Action = {
	label: String;
	handler: () => void;
	icon: string;
	component?: any;
};

const props = defineProps({
	options: {
		type: Array as PropType<Option[]>,
		default: () => []
	},
	modelValue: {},
	placeholder: {
		type: String,
		default: ''
	},
	label: {
		type: String,
		default: ''
	},
	// Allow user to input value that is not in the options
	allowInputAsOption: {
		type: Boolean,
		default: false
	},
	actionButton: {
		type: Object as PropType<Action>,
		default: null
	}
});

const query = ref('');
const multiple = computed(() => Array.isArray(props.modelValue));
const nullable = computed(() => !multiple.value);
const filteredOptions = ref(props.options);

const getDisplayValue = (option: Option | Option[]) => {
	if (Array.isArray(option)) {
		return option.map(o => o.label).join(', ');
	} else if (option) {
		return option.label || option.value || '';
	} else {
		return '';
	}
};

const value = computed(() => {
	if (!props.modelValue) {
		return null;
	}
	return (
		filteredOptions.value.find(option => option.value === props.modelValue) || {
			label: props.modelValue,
			value: props.modelValue
		}
	);
}) as ComputedRef<Option>;

watch(() => query.value || props.options, updateOptions, { immediate: true });

async function updateOptions() {
	if (!query.value) {
		filteredOptions.value = props.options;
	} else {
		filteredOptions.value = props.options.filter(option => {
			const label = option.label.toLowerCase();
			const value = option.label.toLowerCase();
			const queryLower = query.value.toLowerCase();
			return label.includes(queryLower) || value.includes(query.value);
		});
	}
}

function handleQueryChange(event: Event) {
	query.value = (event.target as HTMLInputElement).value;
	if (props.allowInputAsOption && !filteredOptions.value.length) {
		emit('update:modelValue', query.value);
	}
}

const clearValue = () => emit('update:modelValue', null);
</script>
