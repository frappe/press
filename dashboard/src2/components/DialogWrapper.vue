<template>
	<Dialog v-model="show" :options="options">
		<template #body-content>
			<slot />
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'DialogWrapper',
	props: ['modelValue', 'options'],
	emits: ['update:modelValue'],
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	}
};
</script>
