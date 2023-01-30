<template>
	<FrappeUIDialog
		v-model="show"
		:options="{ size: 'lg', position: 'top' }"
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
						:key="`${option.doctype}:${option.name}`"
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
	</FrappeUIDialog>
</template>

<script>
import {
	Combobox,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption
} from '@headlessui/vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

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
	mounted() {
		this.makeFuse();
	},
	methods: {
		onInput(e) {
			let query = e.target.value;
			if (query) {
				this.filteredOptions = this.fuse
					.search(query)
					.map(result => result.item);
			}
		},
		onSelection(value) {
			if (value) {
				this.$router.push(value.route);
			}
		},
		async makeFuse() {
			let list = await this.$call('press.api.account.fuse_list');
			let fuse_list = list;
			for (let item of fuse_list) {
				item.route =
					`/${
						item.doctype.toLowerCase() + (item.doctype === 'Bench' ? 'es' : 's')
					}/` +
					item.route +
					'/overview';
			}

			const options = {
				limit: 10,
				minMatchCharLength: 3,
				keys: ['title'],
				threshold: 0.3
			};
			this.fuse = new Fuse(fuse_list, options);
		}
	}
};
</script>
