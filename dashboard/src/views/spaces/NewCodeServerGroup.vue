<template>
	<div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
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
	props: ['modelValue', 'options'],
	emits: ['update:modelValue', 'error'],
	methods: {
		selectGroup(group) {
			this.$emit('update:modelValue', group);
		}
	},
	computed: {
		groups() {
			return this.options['groups'].filter(group => group.benches.length > 0);
		}
	}
};
</script>
