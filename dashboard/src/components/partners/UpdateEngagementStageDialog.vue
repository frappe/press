<template>
	<Dialog v-model="show" :options="{ title: 'Update Engagement Stage' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					:required="true"
					v-model="proposed_plan"
					label="Proposed Plan"
					type="select"
					name="proposed_plan"
					:options="sitePlanOptions"
				/>
				<FormControl
					v-model="expected_close_date"
					label="Expected Close Date"
					type="date"
					name="expected_close_date"
					:required="true"
				/>
				<ErrorMessage :message="errorMessage" />
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
import { DashboardError } from '../../utils/error';

const emit = defineEmits(['update']);
const show = defineModel();
const errorMessage = ref('');
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
	status: {
		type: String,
		required: true,
	},
});

const sitePlans = getPlans();
const sitePlanOptions = ref(
	sitePlans.map((plan) => ({
		label: plan.name,
		value: plan.name,
	})),
);

const proposed_plan = ref();
const expected_close_date = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: props.status,
			proposed_plan: proposed_plan.value,
			expected_close_date: expected_close_date.value,
		};
	},
	validate: () => {
		if (
			proposed_plan.value === undefined ||
			expected_close_date.value === undefined
		) {
			let error = 'Please select a Proposed Plan and Expected Close Date';
			errorMessage.value = error;
			throw new DashboardError(error);
		}
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});
</script>
