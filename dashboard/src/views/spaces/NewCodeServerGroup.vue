<template>
	<div>
		<div>
			<label class="text-lg font-semibold"> Choose a Bench </label>
			<p class="text-base text-gray-700">
				Choose a bench where you want to install the code server.
			</p>
		</div>
		<FormControl
			class="my-2"
			placeholder="Search for Bench"
			v-on:input="e => updateSearchTerm(e)"
		/>
		<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
			<div
				v-for="group in filteredOptions"
				v-on:click="selectGroup(group)"
				class="m-2 rounded-md border px-6 py-5 text-lg shadow-sm hover:cursor-pointer hover:shadow-md"
				:class="[
					modelValue && modelValue.name == group.name
						? 'relative ring-2 ring-inset ring-blue-500'
						: ''
				]"
			>
				{{ group.title }}
			</div>
		</div>
	</div>
</template>

<script>
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'NewCodeServerBench',
	props: ['modelValue'],
	emits: ['update:modelValue', 'error'],
	data() {
		return {
			filteredOptions: []
		};
	},
	resources: {
		options() {
			return {
				method: 'press.api.spaces.code_server_group_options',
				auto: true,
				onSuccess(data) {
					this.fuse = new Fuse(data, {
						keys: ['title']
					});
					this.filteredOptions = data;
				}
			};
		}
	},
	computed: {
		groups() {
			return this.$resources.options.data;
		}
	},
	methods: {
		selectGroup(group) {
			this.$emit('update:modelValue', group);
		},
		updateSearchTerm(value) {
			if (value) {
				this.filteredOptions = this.fuse
					.search(value)
					.map(result => result.item);
			} else {
				this.filteredOptions = this.$resources.options.data;
			}
		}
	}
};
</script>
