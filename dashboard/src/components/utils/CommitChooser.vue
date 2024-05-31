<template>
	<Autocomplete :options="options" v-model="chosenCommit">
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
	computed: {
		chosenCommit: {
			get() {
				this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', {
					label: this.isVersion(value.label)
						? value.label
						: value.label.match(/\((\w+)\)$/)[1],
					value: value.value
				});
			}
		}
	},
	methods: {
		isVersion(tag) {
			return tag.match(/^v\d+\.\d+\.\d+$/);
		}
	}
};
</script>
