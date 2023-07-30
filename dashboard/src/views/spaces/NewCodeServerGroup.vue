<template>
	<div>
		<div class="ml-2">
			<label class="text-lg font-semibold"> Choose a Bench </label>
			<p class="text-base text-gray-700">
				Choose a bench where you want to install the code server.
			</p>
		</div>
		<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
			<div
				v-for="group in groups"
				v-on:click="selectGroup(group)"
				class="border rounded-md m-2 px-6 py-5 shadow-sm hover:shadow-md hover:cursor-pointer"
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
export default {
	name: 'NewCodeServerBench',
	props: ['modelValue'],
	emits: ['update:modelValue', 'error'],
	methods: {
		selectGroup(group) {
			this.$emit('update:modelValue', group);
		}
	},
	resources: {
		options() {
			return {
				method: 'press.api.spaces.code_server_group_options',
				auto: true
			};
		}
	},
	computed: {
		groups() {
			return this.$resources.options.data;
		}
	}
};
</script>
