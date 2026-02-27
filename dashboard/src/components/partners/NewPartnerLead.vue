<template>
	<Dialog v-model="show" :options="{ title: 'New Lead', size: '2xl' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<div
					v-for="section in sections"
					:key="section.name"
					class="grid gap-4"
					:class="'grid-cols-' + section.columns"
				>
					<div v-for="field in section.fields" :key="field.name">
						<FormControl
							v-model="leadInfo[field.fieldname]"
							:label="field.label || field.fieldname"
							:type="getInputType(field)"
							:name="field.fieldname"
							:options="field.options"
							:required="field.required"
						/>
					</div>
				</div>
				<ErrorMessage :message="errorMessage" />
				<div>
					<Button
						class="w-full"
						variant="solid"
						label="Create Lead"
						@click="_newLeadInfo"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	FormControl,
	createResource,
	createListResource,
} from 'frappe-ui';
import { toast } from 'vue-sonner';
import { computed, ref } from 'vue';
import { DashboardError } from '../../utils/error';

const leadInfo = ref({
	organization_name: '',
	domain: '',
	full_name: '',
	email: '',
	contact_no: '',
	country: '',
	state: '',
	requirement: '',
	status: '',
});
const show = defineModel();

const _domainList = [
	'Distribution',
	'Manufacturing',
	'Agriculture',
	'Retail',
	'Education',
	'Healthcare',
	'Services',
	'Non Profit',
	'Other',
];

const domainList = computed(() => {
	return _domainList.map((domain) => ({
		label: domain,
		value: domain,
	}));
});

const _leadTypeList = createListResource({
	doctype: 'Partner Lead Type',
	fields: ['name'],
	cache: 'leadTypeList',
	auto: true,
});
const leadTypeList = computed(() => {
	return (_leadTypeList.data || []).map((type) => ({
		label: type.name,
		value: type.name,
	}));
});

const _countryList = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
});

const countryList = computed(() => {
	return (_countryList.data || []).map((d) => ({
		label: d.name,
		value: d.name,
	}));
});

const errorMessage = ref('');
const newLeadInfo = createResource({
	url: 'press.api.partner.add_new_lead',
	makeParams: () => {
		return {
			lead_details: leadInfo.value,
		};
	},
	validate: async () => {
		let error = await validate();
		if (error) {
			errorMessage.value = error;
			throw new DashboardError(error);
		}
	},
	onSuccess: () => {
		toast.success('New Lead created successfully');
		show.value = false;
	},
	onError: () => {
		toast.error('Failed to create lead');
	},
});

function _newLeadInfo() {
	newLeadInfo.submit();
}

async function validate() {
	// validate mandatory fields
	for (let field of sections.value.flatMap((s) => s.fields)) {
		if (field.required && !leadInfo.value[field.fieldname]) {
			return `${field.label} is required`;
		}
	}
}

const _indianStates = [
	'Andaman and Nicobar Islands',
	'Andhra Pradesh',
	'Arunachal Pradesh',
	'Assam',
	'Bihar',
	'Chandigarh',
	'Chhattisgarh',
	'Dadra and Nagar Haveli and Daman and Diu',
	'Delhi',
	'Goa',
	'Gujarat',
	'Haryana',
	'Himachal Pradesh',
	'Jammu and Kashmir',
	'Jharkhand',
	'Karnataka',
	'Kerala',
	'Ladakh',
	'Lakshadweep Islands',
	'Madhya Pradesh',
	'Maharashtra',
	'Manipur',
	'Meghalaya',
	'Mizoram',
	'Nagaland',
	'Odisha',
	'Other Territory',
	'Puducherry',
	'Punjab',
	'Rajasthan',
	'Sikkim',
	'Tamil Nadu',
	'Telangana',
	'Tripura',
	'Uttar Pradesh',
	'Uttarakhand',
	'West Bengal',
];

const indianStates = computed(() => {
	return _indianStates.map((state) => ({
		label: state,
		value: state,
	}));
});

const sections = computed(() => {
	return [
		{
			name: 'Company Information',
			columns: 2,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'organization_name',
					label: 'Organization Name',
					required: true,
				},
				{
					fieldtype: 'Select',
					fieldname: 'domain',
					label: 'Domain',
					options: domainList.value,
					required: true,
				},
			],
		},
		{
			name: 'Lead name and Status',
			columns: 2,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'lead_name',
					label: 'Lead Name',
					required: true,
				},
				{
					fieldtype: 'Select',
					fieldname: 'lead_type',
					label: 'Lead Type',
					options: leadTypeList.value,
					required: true,
				},
			],
		},
		{
			name: 'Lead Name',
			columns: 1,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'full_name',
					label: 'Full Name',
					required: true,
				},
			],
		},
		{
			name: 'Contact Information',
			columns: 2,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'email',
					label: 'Email',
					required: true,
				},
				{
					fieldtype: 'Data',
					fieldname: 'contact_no',
					label: 'Contact No.',
				},
			],
		},
		{
			name: 'Country and State',
			columns: 2,
			fields: [
				{
					fieldtype: 'Select',
					fieldname: 'country',
					label: 'Country',
					options: countryList.value,
					required: true,
				},
				{
					fieldtype: leadInfo.value.country === 'India' ? 'Select' : 'Data',
					fieldname: 'state',
					label: 'State / Region',
					required: leadInfo.value.country === 'India' ? true : false,
					options:
						leadInfo.value.country === 'India' ? indianStates.value : null,
				},
			],
		},
		{
			name: 'Requirements',
			columns: 1,
			fields: [
				{
					fieldtype: 'Text',
					fieldname: 'requirement',
					label: 'Requirements',
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
</script>
