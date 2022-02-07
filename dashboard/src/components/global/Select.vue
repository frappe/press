<template>
	<label class="block">
		<span
			v-if="label"
			class="mb-2 inline-block text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-if="type !== 'select'"
			class="form-input block w-full"
			:class="inputClass"
			:type="type || 'text'"
			v-bind="$attrs"
			v-model="inputVal"
		/>
		<select class="form-select block w-full" v-model="inputVal" v-else>
			<option v-for="option in options" :key="option">
				{{ option }}
			</option>
		</select>
	</label>
</template>

<script>
export default {
	name: 'Input',
	props: ['label', 'type', 'value', 'inputClass', 'options'],
	computed: {
		inputVal: {
			get() {
				return this.value;
			},
			set(val) {
				this.$emit('input', val);
			}
		}
	}
};
</script>
