<template>
	<div class="space-y-4">
		<div v-for="field in fields" :key="field.fieldname">
			<Input
				:label="field.label || field.fieldname"
				:type="getInputType(field)"
				:options="field.options"
				:name="field.fieldname"
				:value="values[field.fieldname]"
				@change="onChange($event, field)"
				@blur="checkRequired(field, $event)"
				:required="field.required || false"
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
		getInputType(field) {
			return {
				Data: 'text',
				Int: 'number',
				Select: 'select',
				Check: 'checkbox',
				Password: 'text'
			}[field.fieldtype || 'Data'];
		}
	}
};
</script>
