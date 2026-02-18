<template>
	<Dialog v-model="show" :options="{ title: 'Lead Details', size: '2xl' }">
		<template #body-content>
			<LeadDetailsForm @success="() => emit('success')" v-model="leadInfo" />
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, createResource } from 'frappe-ui';
import LeadDetailsForm from './LeadDetailsForm.vue';
import { useRoute } from 'vue-router';
import { reactive } from 'vue';

const show = defineModel();
const emit = defineEmits(['success']);
const route = useRoute();

const leadInfo = reactive({
	organization_name: '',
	domain: '',
	lead_name: '',
	full_name: '',
	email: '',
	contact_no: '',
	country: '',
	state: '',
	status: '',
	engagement_stage: '',
});

createResource({
	url: 'press.api.partner.get_lead_details',
	auto: true,
	makeParams: () => {
		return { lead_id: route.params.leadId };
	},
	onSuccess: (data) => {
		if (!data) return '';
		Object.assign(leadInfo, {
			organization_name: data.organization_name || '',
			domain: data.domain || '',
			lead_name: data.lead_name || '',
			full_name: data.full_name || '',
			email: data.email || '',
			contact_no: data.contact_no || '',
			country: data.country || '',
			state: data.state || '',
			status: data.status || '',
			probability: data.probability || 0,
			requirement: data.requirement || '',
			plan_proposed: data.plan_proposed || '',
			engagement_stage: data.engagement_stage || '',
		});
	},
});
</script>
