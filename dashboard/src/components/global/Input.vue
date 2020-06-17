<template>
	<label :class="type == 'checkbox' ? 'flex' : 'block'">
		<span
			v-if="label && type != 'checkbox'"
			class="block mb-2 text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-if="type !== 'select'"
			class="placeholder-gray-500"
			:class="[
				{
					'block w-full form-input': type != 'checkbox',
					'form-checkbox': type == 'checkbox'
				},
				inputClass
			]"
			:type="type || 'text'"
			v-bind="$attrs"
			v-model="inputVal"
		/>
		<select class="block w-full form-select" v-model="inputVal" v-else>
			<option
				v-for="option in selectOptions"
				:key="option.value"
				:value="option.value"
				:disabled="!option.value"
				:selected="inputVal === option.value"
			>
				{{ option.label }}
			</option>
		</select>
		<span
			v-if="label && type == 'checkbox'"
			class="inline-block ml-2 text-base leading-4"
		>
			{{ label }}
		</span>
	</label>
</template>

<script>
export default {
	name: 'Input',
	inheritAttrs: false,
	props: ['label', 'type', 'value', 'inputClass', 'options'],
	computed: {
		inputVal: {
			get() {
				return this.value;
			},
			set(val) {
				this.$emit('input', val);
				this.$emit('change', val);
			}
		},
		selectOptions() {
			return this.options.map(option => {
				if (typeof option === 'string') {
					return {
						label: option,
						value: option
					};
				}
				return option;
			});
		}
	}
};
</script>
