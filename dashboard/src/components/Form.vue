<template>
	<div class="space-y-4">
		<label class="block" v-for="field in fields" :key="field.fieldname">
			<span class="text-gray-800">{{ field.label || field.fieldname }}</span>
			<select
				class="block w-full mt-2 shadow form-select"
				:name="field.fieldname"
				v-if="field.fieldtype === 'Select'"
				@change="onChange($event, field)"
				@blur="checkRequired(field, $event.target.value)"
			>
				<option
					v-for="option in field.options"
					:value="option.value"
					:key="option.value"
					:disabled="!option.value"
					:selected="values[field.fieldname] === option.value"
				>
					{{ option.label }}
				</option>
			</select>
			<input
				v-else
				class="block w-full mt-2 shadow form-input"
				:type="getInputType(field)"
				:name="field.fieldname"
				:value="values[field.fieldname]"
				@change="onChange($event, field)"
				@blur="checkRequired(field, $event.target.value)"
				:required="field.required || false"
			/>
			<ErrorMessage
				class="mt-1"
				v-if="requiredFieldNotSet.includes(field)"
				error="This field is required"
			/>
		</label>
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
		onChange(e, field) {
			let value = e.target.value;
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
				Int: 'number'
			}[field.fieldtype || 'Data'];
		}
	}
};
</script>
