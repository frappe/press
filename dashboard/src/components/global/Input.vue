<template>
	<label :class="type == 'checkbox' ? 'flex' : 'block'">
		<span
			v-if="label && type != 'checkbox'"
			class="block mb-2 text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-if="['text', 'number', 'checkbox', 'email', 'password'].includes(type)"
			class="placeholder-gray-500"
			:class="[
				{
					'block w-full form-input': type != 'checkbox',
					'form-checkbox': type == 'checkbox'
				},
				inputClass
			]"
			:type="type || 'text'"
			:disabled="disabled"
			v-bind="$attrs"
			@blur="$emit('blur', $event)"
			v-model="inputVal"
		/>
		<textarea
			v-if="type === 'textarea'"
			:class="['block w-full resize-none form-textarea', inputClass]"
			v-model="inputVal"
			:disabled="disabled"
			v-bind="$attrs"
			rows="3"
			@blur="$emit('blur', $event)"
		></textarea>
		<select
			class="block w-full form-select"
			v-model="inputVal"
			v-if="type === 'select'"
			:disabled="disabled"
		>
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
	props: {
		label: {
			type: String
		},
		type: {
			type: String,
			validator(value) {
				let isValid = [
					'text',
					'number',
					'checkbox',
					'textarea',
					'select',
					'email',
					'password'
				].includes(value);
				if (!isValid) {
					console.warn(`Invalid value "${value}" for "type" prop for Input`);
				}
				return isValid;
			}
		},
		value: {
			type: [String, Number, Boolean, Object, Array]
		},
		inputClass: {
			type: [String, Array, Object]
		},
		options: {
			type: Array
		},
		disabled: {
			type: Boolean
		}
	},
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
