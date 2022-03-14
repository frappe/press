<template>
	<div class="space-y-4">
		<div
			v-for="field in fields"
			:key="field.fieldname"
			v-show="field.condition ? field.condition() : true"
		>
			<div class="flex space-x-4" v-if="Array.isArray(field)">
				<Input
					v-bind="getBindProps(subfield)"
					:key="subfield.fieldname"
					class="w-full"
					v-for="subfield in field"
					v-on="getBindListeners(subfield)"
				/>
			</div>
			<Input
				v-else
				v-bind="getBindProps(field)"
				v-on="getBindListeners(field)"
			/>
			<ErrorMessage
				class="mt-1"
				v-if="requiredFieldNotSet.includes(field)"
				error="This field is required"
			/>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Form',
	props: ['fields', 'values'],
	model: {
		event: 'change',
		prop: 'values'
	},
	data() {
		return {
			requiredFieldNotSet: []
		};
	},
	methods: {
		onChange(value, field) {
			this.checkRequired(field, value);
			this.updateValue(field.fieldname, value);
		},
		updateValue(fieldname, value) {
			let values = Object.assign({}, this.values, {
				[fieldname]: value
			});
			this.$emit('change', values);
		},
		checkRequired(field, value) {
			if (field.required) {
				if (!value) {
					this.requiredFieldNotSet.push(field);
					return false;
				} else {
					this.requiredFieldNotSet = this.requiredFieldNotSet.filter(
						f => f !== field
					);
				}
			}
			return true;
		},
		getBindProps(field) {
			return {
				label: field.label || field.fieldname,
				type: this.getInputType(field),
				options: field.options,
				name: field.fieldname,
				value: this.values[field.fieldname],
				disabled: field.disabled,
				required: field.required || false,
				rows: field.rows,
				placeholder: field.placeholder
			};
		},
		getBindListeners(field) {
			return {
				change: e => this.onChange(e, field),
				blur: e => this.checkRequired(field, e)
			};
		},
		getInputType(field) {
			return {
				Data: 'text',
				Int: 'number',
				Select: 'select',
				Check: 'checkbox',
				Password: 'password',
				Text: 'textarea'
			}[field.fieldtype || 'Data'];
		}
	}
};
</script>
