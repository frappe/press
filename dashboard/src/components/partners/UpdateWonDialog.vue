<template>
	<Dialog v-model="show" :options="{ title: 'Add Conversion Date' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="conversion_date"
					label="Conversion Date"
					type="date"
					name="conversion_date"
				/>
				<Button variant="solid" @click="() => updateStatus.submit()"
					>Submit</Button
				>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, FormControl, createResource } from 'frappe-ui';
import { ref, defineEmits } from 'vue';

const emit = defineEmits(['update']);
const show = defineModel();
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
});

const conversion_date = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'Won',
			conversion_date: conversion_date.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});
</script>
