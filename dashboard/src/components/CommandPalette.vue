<template>
	<Dialog
		:modelValue="show"
		:options="{ size: 'xl', position: 'top' }"
		@after-leave="
			() => {
				$emit('close', true);
				filteredOptions = [];
			}
		"
	>
		<template #body>
			<Combobox @update:model-value="onSelection">
				<ComboboxInput
					@keyup.enter="show = false"
					placeholder="Search for sites, benches and servers"
					class="w-full border-none bg-transparent px-4 text-base text-gray-800 placeholder-gray-500 focus:ring-0"
					@input="onInput"
					autocomplete="off"
				/>
				<ComboboxOptions
					@mousedown="show = false"
					class="max-h-96 overflow-auto border-t border-gray-100"
					static
				>
					<ComboboxOption
						v-for="option in filteredOptions"
						:key="`${option.route}`"
						v-slot="{ active }"
						:value="option"
					>
						<div
							class="flex w-full items-center px-4 py-2 text-base text-gray-900"
							:class="{ 'bg-gray-200': active }"
						>
							<span> {{ option.title }}&nbsp; </span>
							<span class="ml-auto text-gray-600">
								{{ option.doctype }}
							</span>
						</div>
					</ComboboxOption>
				</ComboboxOptions>
			</Combobox>
		</template>
	</Dialog>
</template>

<script>
import {
	Combobox,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption
} from '@headlessui/vue';
import { debounce } from 'lodash';

export default {
	name: 'CommandPalette',
	props: {
		show: false
	},
	data() {
		return {
			filteredOptions: []
		};
	},
	components: {
		Combobox,
		ComboboxInput,
		ComboboxOptions,
		ComboboxOption
	},
	methods: {
		onInput: debounce(async function (e) {
			const query = e.target.value;
			if (query) {
				const list = await this.$call('press.utils.search.search', {
					text: query
				});
				this.filteredOptions = list.map(item => {
					if (item.doctype === 'Release Group')
						return { ...item, doctype: 'Bench' };
					return item;
				});
			}
		}, 400),
		onSelection(value) {
			if (value) {
				this.$router.push(value.route);
			}
		}
	}
};
</script>
