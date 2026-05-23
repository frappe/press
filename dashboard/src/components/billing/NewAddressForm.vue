<template>
	<div>
		<div class="flex flex-col gap-5">
			<div
				v-for="section in sections"
				:key="section.name"
				class="grid gap-4"
				:class="'grid-cols-' + section.columns"
			>
				<div v-for="field in section.fields" :key="field.name">
					<FormControl
						v-model="billingInformation[field.fieldname]"
						:label="field.label || field.fieldname"
						:type="getInputType(field)"
						:name="field.fieldname"
						:options="field.options"
						:disabled="props.disableForm"
						:required="field.required"
					/>
				</div>
			</div>
			<div v-show="billingInformation.country == 'Algeria'">
				<FormControl
					label="I have NIF"
					type="checkbox"
					:disabled="props.disableForm"
					v-model="gstApplicable"
				/>
				<FormControl
					v-if="gstApplicable"
					class="mt-5"
					label="NIF"
					type="text"
					:disabled="props.disableForm"
					v-model="billingInformation.gstin"
				/>
			</div>
		</div>
		<ErrorMessage class="mt-2" :message="updateBillingInformation.error" />
	</div>
</template>
<script setup>
import { FormControl, ErrorMessage, createResource } from 'frappe-ui';
import { ref, computed, inject, watch } from 'vue';
import { toast } from 'vue-sonner';
import { DashboardError } from '../../utils/error';
import { algerianWilayas } from '@/utils/billing.js';

const emit = defineEmits(['success']);
const team = inject('team');

const billingInformation = defineModel();
const props = defineProps({
	disableForm: { type: Boolean, default: false },
});

const updateBillingInformation = createResource({
	url: 'press.api.account.update_billing_information',
	makeParams: () => {
		return { billing_details: billingInformation.value };
	},
	validate: async () => {
		let error = await validate();
		if (error) throw new DashboardError(error);
	},
	onSuccess: () => {
		toast.success('Billing information updated');
		emit('success');
	},
});

const gstApplicable = ref(false);

watch(
	() => billingInformation.value.gstin,
	(gstin) => {
		gstApplicable.value = gstin && gstin !== 'Not Applicable';
	},
);

async function validate() {
	// validate mandatory fields
	for (let field of sections.value.flatMap((s) => s.fields)) {
		if (field.required && !billingInformation.value[field.fieldname]) {
			return `${field.label} is required`;
		}
	}

	if (!gstApplicable.value) {
		billingInformation.value.gstin = 'Not Applicable';
	}

	// validate NIF
	return await validateNIF();
}


const _countryList = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
	onSuccess: () => {
		let userCountry = team.doc?.country;
		if (userCountry) {
			let country = countryList.value?.find((d) => d.label === userCountry);
			if (country) {
				billingInformation.value.country = country.value;
			}
		}
	},
});

const countryList = computed(() => {
	return (_countryList.data || []).map((d) => ({
		label: d.name,
		value: d.name,
	}));
});

const algerianWilayaOptions = computed(() => {
	return algerianWilayas.map((state) => ({
		label: state,
		value: state,
	}));
});

const sections = computed(() => {
	return [
		{
			name: 'Country and City',
			columns: 2,
			fields: [
				{
					fieldtype: 'Select',
					label: 'Country',
					fieldname: 'country',
					options: countryList.value,
					required: true,
				},
				{
					fieldtype: 'Data',
					label: 'City',
					fieldname: 'city',
					required: true,
				},
			],
		},
		{
			name: 'Address',
			columns: 1,
			fields: [
				{
					fieldtype: 'Data',
					label: 'Address',
					fieldname: 'address',
					required: true,
				},
			],
		},
		{
			name: 'State and Postal Code',
			columns: 2,
			fields: [
				{
					fieldtype:
						billingInformation.value.country === 'Algeria' ? 'Select' : 'Data',
					label: 'State / Province / Region',
					fieldname: 'state',
					required: true,
					options:
						billingInformation.value.country === 'Algeria'
							? algerianWilayaOptions.value
							: null,
				},
				{
					fieldtype: 'Data',
					label: 'Postal Code',
					fieldname: 'postal_code',
					required: true,
				},
			],
		},
	];
});

function getInputType(field) {
	return {
		Data: 'text',
		Int: 'number',
		Select: 'select',
		Check: 'checkbox',
		Password: 'password',
		Text: 'textarea',
		Date: 'date',
	}[field.fieldtype || 'Data'];
}

const _validateNIF = createResource({
	url: 'press.api.billing.validate_gst',
	params: { address: billingInformation.value },
});

async function validateNIF() {
	billingInformation.value.gstin =
		billingInformation.value.gstin || 'Not Applicable';
	await _validateNIF.submit();
}

defineExpose({ updateBillingInformation, validate });
</script>
