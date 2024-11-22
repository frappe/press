<template>
	<div class="flex flex-col gap-5">
		<div
			v-for="field in fields"
			:key="field.fieldname"
			v-show="field.condition ? field.condition() : true"
		>
			<FormControl v-bind="getBindProps(field)" variant="outline">
				<template #suffix v-if="field.fieldtype === 'Password'">
					<FeatherIcon
						@click="togglePasswordVisibility(field)"
						class="w-4 cursor-pointer"
						:name="
							passwordFieldsAsText.includes(field.fieldname) ? 'eye-off' : 'eye'
						"
					/>
				</template>
			</FormControl>

			<ErrorMessage
				class="mt-1"
				v-if="requiredFieldNotSet.includes(field)"
				error="This field is required"
			/>
		</div>
	</div>
</template>

<script>
import { FeatherIcon } from 'frappe-ui';

// https://github.com/eggert/tz/blob/main/backward add more if required.
const TZ_BACKWARD_COMPATBILITY_MAP = {
	'Asia/Calcutta': 'Asia/Kolkata'
};

export default {
	name: 'Form',
	props: ['fields', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			requiredFieldNotSet: [],
			passwordFieldsAsText: [],
			guessedTimezone: ''
		};
	},
	mounted() {
		this.guessedTimezone = this.guessTimezone();
	},
	watch: {
		fields: {
			handler(new_fields) {
				let timezoneFields = new_fields.filter(
					f => f.fieldtype === 'Select' && f.fieldname.endsWith('_tz')
				);
				for (let field of timezoneFields) {
					if (!field.options) {
						field.options = [];
					}
					if (
						this.guessedTimezone &&
						field.options.includes(this.guessedTimezone)
					) {
						this.onChange(this.guessedTimezone, field);
					}
				}
			},
			deep: true
		}
	},
	methods: {
		onChange(value, field) {
			this.checkRequired(field, value);
			this.updateValue(field.fieldname, value);
		},
		updateValue(fieldname, value) {
			let values = Object.assign({}, this.modelValue, {
				[fieldname]: value
			});
			this.$emit('update:modelValue', values);
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
		togglePasswordVisibility(field) {
			if (this.passwordFieldsAsText.includes(field.fieldname)) {
				this.passwordFieldsAsText = this.passwordFieldsAsText.filter(
					f => f !== field.fieldname
				);
			} else {
				this.passwordFieldsAsText.push(field.fieldname);
			}
		},
		getBindProps(field) {
			return {
				label: field.label || field.fieldname,
				type: this.passwordFieldsAsText.includes(field.fieldname)
					? 'text'
					: this.getInputType(field),
				options: field.options,
				name: field.fieldname,
				modelValue: this.modelValue[field.fieldname],
				disabled: field.disabled,
				required: field.required || false,
				rows: field.rows,
				placeholder: field.placeholder,
				'onUpdate:modelValue': value => this.onChange(value, field),
				onBlur: e => this.checkRequired(field, e)
			};
		},
		getInputType(field) {
			return {
				Data: 'text',
				Int: 'number',
				Select: 'select',
				Check: 'checkbox',
				Password: 'password',
				Text: 'textarea',
				Date: 'date'
			}[field.fieldtype || 'Data'];
		},
		guessTimezone() {
			try {
				let tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
				if (TZ_BACKWARD_COMPATBILITY_MAP[tz]) {
					return TZ_BACKWARD_COMPATBILITY_MAP[tz];
				}
				return tz;
			} catch (e) {
				console.error("Couldn't guess timezone", e);
				return null;
			}
		}
	}
};
</script>
