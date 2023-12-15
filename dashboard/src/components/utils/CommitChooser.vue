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
				class="font-mono text-xs"
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
