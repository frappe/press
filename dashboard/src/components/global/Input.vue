<template>
	<label :class="type == 'checkbox' ? 'flex' : 'block'">
		<span
			v-if="label && type != 'checkbox'"
			class="mb-2 block text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-bind="$attrs"
			v-if="
				['text', 'number', 'checkbox', 'email', 'password', 'date'].includes(
					type
				)
			"
			class="placeholder-gray-500"
			ref="input"
			:class="[
				{
					'form-input block w-full': type != 'checkbox',
					'form-checkbox': type == 'checkbox'
				},
				inputClass
			]"
			:type="type || 'text'"
			:disabled="disabled"
			:placeholder="placeholder"
			v-on="inputListeners"
			:value="modelValue"
		/>
		<textarea
			v-bind="$attrs"
			v-if="type === 'textarea'"
			:class="[
				'form-textarea block w-full resize-none placeholder-gray-500',
				inputClass
			]"
			ref="input"
			:value="modelValue"
			:disabled="disabled"
			:placeholder="placeholder"
			v-on="inputListeners"
			:rows="rows || 3"
			@blur="$emit('blur', $event)"
		></textarea>
		<select
			class="form-select block w-full"
			ref="input"
			v-if="type === 'select'"
			:disabled="disabled"
			v-on="inputListeners"
		>
			<option
				v-for="option in selectOptions"
				:key="option.value"
				:value="option.value"
				:selected="modelValue === option.value"
			>
				{{ option.label }}
			</option>
		</select>
		<span
			v-if="label && type == 'checkbox'"
			class="ml-2 inline-block text-base leading-4"
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
					'password',
					'date'
				].includes(value);
				if (!isValid) {
					console.warn(`Invalid value "${value}" for "type" prop for Input`);
				}
				return isValid;
			}
		},
		modelValue: {
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
		},
		rows: {
			type: Number
		},
		placeholder: {
			type: String
		}
	},
	emits: ['blur', 'update:modelValue', 'change'],
	methods: {
		focus() {
			this.$refs.input.focus();
		},
		blur() {
			this.$refs.input.blur();
		},
		getInputValue(e) {
			let value = e.target.value;
			if (this.type == 'checkbox') {
				value = e.target.checked;
			}
			return value;
		}
	},
	computed: {
		inputListeners() {
			return {
				input: e => {
					this.$emit('update:modelValue', this.getInputValue(e));
				},
				change: e => {
					this.$emit('change', this.getInputValue(e));
				}
			};
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
