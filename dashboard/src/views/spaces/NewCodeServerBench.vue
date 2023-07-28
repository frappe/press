<template>
	<div>
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
