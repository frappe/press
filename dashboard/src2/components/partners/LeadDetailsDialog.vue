<template>
	<Dialog v-model="show" :options="{ title: 'Lead Details' }">
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
});

createResource({
	url: 'press.api.partner.get_lead_details',
	auto: true,
	makeParams: () => {
		// console.log(route)
		return { lead_id: route.params.leadId };
	},
	onSuccess: (data) => {
		if (!data) return '';
		console.log(data);
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
		});
	},
});
</script>
