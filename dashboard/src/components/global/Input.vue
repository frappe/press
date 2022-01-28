<template>
	<label :class="type == 'checkbox' ? 'flex' : 'block'">
		<span
			v-if="label && type != 'checkbox'"
			class="block mb-2 text-sm leading-4 text-gray-700"
		>
			{{ label }}
		</span>
		<input
			v-if="
				['text', 'number', 'checkbox', 'email', 'password', 'date'].includes(
					type
				)
			"
			class="placeholder-gray-500"
			ref="input"
			:class="[
				{
					'block w-full form-input': type != 'checkbox',
					'form-checkbox': type == 'checkbox'
				},
				inputClass
			]"
			:type="type || 'text'"
			:disabled="disabled"
			:placeholder="placeholder"
			v-bind="$attrs"
			v-on="inputListeners"
			:value="value"
		/>
		<textarea
			v-if="type === 'textarea'"
			:class="[
				'block w-full resize-none form-textarea placeholder-gray-500',
				inputClass
			]"
			ref="input"
			:value="value"
			:disabled="disabled"
			:placeholder="placeholder"
			v-bind="$attrs"
			v-on="inputListeners"
			:rows="rows || 3"
			@blur="$emit('blur', $event)"
		></textarea>
		<select
			class="block w-full form-select"
			ref="input"
			v-if="type === 'select'"
			:disabled="disabled"
			v-on="inputListeners"
		>
			<option
				v-for="option in selectOptions"
				:key="option.value"
				:value="option.value"
				:selected="value === option.value"
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
					'password',
					'date'
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
		},
		rows: {
			type: Number
		},
		placeholder: {
			type: String
		}
	},
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
			return Object.assign({}, this.$listeners, {
				input: e => {
					this.$emit('input', this.getInputValue(e));
				},
				change: e => {
					this.$emit('change', this.getInputValue(e));
				}
			});
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
