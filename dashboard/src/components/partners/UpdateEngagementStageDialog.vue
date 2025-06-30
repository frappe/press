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
				<FormControl
					v-if="
						engagement_stage === 'Quotation' ||
						engagement_stage === 'Ready for Closing'
					"
					:required="true"
					v-model="proposed_plan"
					label="Proposed Plan"
					type="select"
					name="proposed_plan"
					:options="sitePlanOptions"
				/>
				<FormControl
					v-if="
						engagement_stage === 'Quotation' ||
						engagement_stage === 'Ready for Closing'
					"
					v-model="expected_close_date"
					label="Expected Close Date"
					type="date"
					name="expected_close_date"
					:required="true"
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
import { getPlans } from '../../data/plans';

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
	'Quotation',
	'Ready for Closing',
];
const engagementStageOptions = ref(
	_engagementStageOptions.map((stage) => ({
		label: stage,
		value: stage,
	})),
);

const sitePlans = getPlans();
const sitePlanOptions = ref(
	sitePlans.map((plan) => ({
		label: plan.name,
		value: plan.name,
	})),
);

const engagement_stage = ref();
const proposed_plan = ref();
const expected_close_date = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'In Process',
			engagement_stage: engagement_stage.value,
			proposed_plan: proposed_plan.value,
			expected_close_date: expected_close_date.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});
</script>
