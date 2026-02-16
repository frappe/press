<template>
	<div class="flex flex-col gap-5">
		<FormControl
			v-model="billingInformation.billing_name"
			type="text"
			name="billing_name"
			label="Billing Name"
			:required="true"
		/>
		<NewAddressForm
			ref="addressFormRef"
			v-model="billingInformation"
			@success="() => emit('success')"
		/>
		<ErrorMessage class="mt-2" :message="errorMessage" />
	</div>
	<div v-if="addressFormRef" class="mt-6">
		<Button
			class="w-full"
			variant="solid"
			label="Update billing details"
			:loading="addressFormRef.updateBillingInformation.loading"
			@click="updateBillingInformation"
		/>
	</div>
</template>
<script setup>
import NewAddressForm from './NewAddressForm.vue';
import { FormControl, ErrorMessage, Button, createResource } from 'frappe-ui';
import { reactive, ref, inject } from 'vue';

const emit = defineEmits(['success']);

const team = inject('team');

const addressFormRef = ref(null);

const fullName = `${team.doc.user_info.first_name || ''} ${
	team.doc.user_info.last_name || ''
}`.trim();

const billingInformation = reactive({
	billing_name: fullName || '',
	address: '',
	city: '',
	state: '',
	postal_code: '',
	country: '',
	gstin: '',
});

createResource({
	url: 'press.api.account.get_billing_information',
	auto: true,
	onSuccess: (data) => {
		if (!Object.keys(data).length) return;

		Object.assign(billingInformation, {
			address: data.address_line1,
			city: data.city,
			state: data.state,
			postal_code: data.pincode,
			country: data.country,
			gstin: data.gstin == 'Not Applicable' ? '' : data.gstin,
			billing_name: data.billing_name,
		});
	},
});

const errorMessage = ref('');

function updateBillingInformation() {
	if (!billingInformation.billing_name) {
		errorMessage.value = 'Billing Name is required';
		return;
	}
	const billing_name = billingInformation.billing_name.trim();
	const billingNameRegex = /^[a-zA-Z0-9\-\'\,\.\(\)\s]+$/;
	const billingNameValid = billingNameRegex.test(billing_name);
	if (!billingNameValid) {
		errorMessage.value = 'Billing Name contains invalid characters';
		return;
	}
	billingInformation.billing_name = billing_name;
	addressFormRef.value.updateBillingInformation.submit();
}
</script>
