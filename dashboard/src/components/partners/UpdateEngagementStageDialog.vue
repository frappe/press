<template>
	<Dialog v-model="show" :options="{ title: 'Update Engagement Stage' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="engagement_stage"
					label="Engagement Stage"
					type="select"
					name="engagement_stage"
					:options="engagementStageOptions"
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
import { defineEmits, ref } from 'vue';

const emit = defineEmits(['update']);
const show = defineModel();
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
});

const _engagementStageOptions = [
	'Demo',
	'Qualification',
	'Learning',
	'Follow-up',
	'Quotation',
	'Negotiation',
	'Ready for Closing',
];
const engagementStageOptions = ref(
	_engagementStageOptions.map((stage) => ({
		label: stage,
		value: stage,
	})),
);

const engagement_stage = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'In Process',
			engagement_stage: engagement_stage.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});
</script>
