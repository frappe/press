<template>
	<Dialog v-model="show" :options="{ title: 'New Audit Request' }">
		<template #body-content>
			<div
				class="text-base mb-4 text-yellow-600 bg-yellow-100 p-4 rounded leading-normal"
			>
				Our team will get back to you within 2 working days to confirm the audit
				date and share the checklist for the audit.
			</div>
			<div class="text-gray-600 text-base">
				Pick a Audit Date
				<DatePicker class="mt-2" v-model="audit_date" :format="'DD-MM-YYYY'" />
				<FormControl
					type="select"
					v-model="audit_type"
					label="Audit Type"
					:options="[
						{ label: 'Online', value: 'Online' },
						{ label: 'In-Person', value: 'In-Person' },
					]"
					class="mt-4"
				/>
			</div>
			<ErrorMessage :message="errorMessage" class="mt-4" />
			<Button
				class="mt-4 w-full"
				variant="solid"
				label="Request Audit"
				@click="
					() => {
						newAuditRequest.submit();
					}
				"
			/>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, DatePicker, createResource } from 'frappe-ui';
import { ref } from 'vue';
import { toast } from 'vue-sonner';

const show = defineModel();
const audit_date = ref('');
const audit_type = ref('Online');
const errorMessage = ref('');

const newAuditRequest = createResource({
	url: 'press.api.partner.create_audit_request',
	makeParams: () => {
		return {
			audit_date: audit_date.value,
			audit_type: audit_type.value,
		};
	},
	onSuccess: () => {
		toast.success('Audit request created successfully');
		show.value = false;
	},
	onError: (err) => {
		errorMessage.value = err.messages[0] || 'Failed to create audit request';
	},
});
</script>
