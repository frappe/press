<template>
	<Autocomplete
		:options="options"
		:value="modelValue"
		@change="
			e =>
				$emit('update:modelValue', {
					// get only the commit hash if release not tagged
					label: isVersion(e.label) ? e.label : e.label.match(/\((\w+)\)$/)[1],
					value: e.value
				})
		"
	>
		<template v-slot:target="{ togglePopover }">
			<Button
				class="flex w-fit items-center rounded-full bg-gray-100 px-2 py-1 font-mono text-xs font-normal leading-[13px] text-gray-800 hover:bg-gray-200"
				:label="modelValue.label"
				icon-right="chevron-down"
				@click="() => togglePopover()"
			/>
		</template>
	</Autocomplete>
</template>

<script>
export default {
	name: 'CommitChooser',
	props: ['options', 'modelValue'],
	emits: ['update:modelValue'],
	methods: {
		isVersion(tag) {
			return tag.match(/^v\d+\.\d+\.\d+$/);
		}
	}
};
</script>
