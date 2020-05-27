<template>
	<label class="block">
		<span
			v-if="label"
			class="inline-block mb-2 text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-if="type !== 'select'"
			class="block w-full form-input"
			:class="inputClass"
			:type="type || 'text'"
			v-bind="$attrs"
			v-model="inputVal"
		/>
		<select class="block w-full form-select" v-model="inputVal" v-else>
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
