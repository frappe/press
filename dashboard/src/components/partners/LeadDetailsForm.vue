<template>
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
					:disabled="props.disableForm"
					:required="field.required"
				/>
			</div>
		</div>
		<ErrorMessage :message="errorMessage" />
		<div>
			<Button
				class="w-full"
				variant="solid"
				label="Update Lead details"
				@click="_updateLeadInfo"
			/>
		</div>
	</div>
</template>
<script setup>
import { FormControl, createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { computed, ref } from 'vue';
import { DashboardError } from '../../utils/error';
import { useRoute } from 'vue-router';

const emit = defineEmits(['success']);
const route = useRoute();
const errorMessage = ref('');

const leadInfo = defineModel();
const props = defineProps({
	disableForm: { type: Boolean, default: false },
});

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

const _statusList = [
	'Won',
	'Open',
	'Lost',
	'In Process',
	'Junk',
	'Passed to Other Partner',
];

const statusList = computed(() => {
	return _statusList.map((status) => ({
		label: status,
		value: status,
	}));
});

const probability = computed(() => {
	return [
		{ label: 'Hot', value: 'Hot' },
		{ label: 'Warm', value: 'Warm' },
		{ label: 'Cold', value: 'Cold' },
	];
});

const _countryList = createResource({
	url: 'press.api.account.country_list',
	cache: 'countryList',
	auto: true,
	onSuccess: () => {
		let leadCountry = leadInfo.value.country;
		if (leadCountry) {
			let country = countryList.value?.find((d) => d.label === leadCountry);
			if (country) {
				leadInfo.value.country = country.value;
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

const _planList = createResource({
	url: 'press.api.partner.get_fc_plans',
	auto: true,
	cache: 'planList',
	onSuccess: (data) => {
		// console.log('Plan List', data);
	},
});

const planList = computed(() => {
	return (_planList.data || []).map((plan) => ({
		label: plan,
		value: plan,
	}));
});

const updateLeadInfo = createResource({
	url: 'press.api.partner.update_lead_details',
	makeParams: () => {
		return {
			lead_name: route.params.leadId,
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
		toast.success('Lead Information updated');
		emit('success');
	},
});

function _updateLeadInfo() {
	updateLeadInfo.submit();
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

const _engagementStageOptions = [
	'Demo',
	'Qualification',
	'Quotation',
	'Ready for Closing',
];
const engagementStageOptions = ref(
	_engagementStageOptions.map((stage) => ({
		label: stage,
		value: stage,
	})),
);

const sections = computed(() => {
	return [
		{
			name: 'Company Information',
			columns: 1,
			fields: [
				{
					fieldtype: 'Data',
					fieldname: 'organization_name',
					label: 'Organization Name',
					required: true,
				},
			],
		},
		{
			name: 'Engagement Stage and Status',
			columns: 2,
			fields: [
				{
					fieldtype: 'Select',
					fieldname: 'engagement_stage',
					label: 'Engagement Stage',
					options: engagementStageOptions.value,
					required: true,
				},
				{
					fieldtype: 'Select',
					fieldname: 'status',
					label: 'Status',
					options: statusList.value,
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
					required: true,
					options:
						leadInfo.value.country === 'India' ? indianStates.value : null,
				},
			],
		},
		{
			name: 'Domain',
			columns: 1,
			fields: [
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
			name: 'Deal details',
			columns: 2,
			fields: [
				{
					fieldtype: 'Select',
					fieldname: 'probability',
					label: 'Probability',
					options: probability.value,
				},
				{
					fieldtype: 'Select',
					fieldname: 'plan_proposed',
					label: 'Plan Proposed',
					options: planList.value,
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
