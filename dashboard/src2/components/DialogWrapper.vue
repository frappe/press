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
	data() {
		return {
			_show: true
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue != null ? this.modelValue : this._show;
			},
			set(value) {
				if (this.modelValue != null) {
					this.$emit('update:modelValue', value);
				} else {
					this._show = value;
				}
			}
		}
	}
};
</script>
