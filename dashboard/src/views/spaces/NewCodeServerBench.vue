<template>
	<div>
		<div class="ml-2">
			<label class="text-lg font-semibold"> Choose a Bench </label>
			<p class="text-base text-gray-700">
				Choose a bench where you want to install the code server.
			</p>
		</div>
		<ListItem
			v-for="(bench, index) in benches"
			:key="bench.name"
			:title="bench.name"
			class="border rounded-md m-2 px-2 shadow-sm hover:shadow-md hover:cursor-pointer"
			:class="[
				modelValue && modelValue == bench.name
					? 'relative ring-2 ring-inset ring-blue-500'
					: ''
			]"
			v-on:click="selectBench(bench)"
		>
			<template #actions>
				<Badge
					v-if="index === 0"
					label="Latest Deployed"
					:colorMap="$badgeStatusColorMap"
				></Badge>
			</template>
		</ListItem>
	</div>
</template>

<script>
export default {
	name: 'NewCodeServerBench',
	props: ['modelValue', 'benches'],
	emits: ['update:modelValue', 'error'],
	methods: {
		selectBench(bench) {
			this.$emit('update:modelValue', bench.name);
		}
	}
};
</script>
