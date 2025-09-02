<template>
	<Dialog v-model="show" :options="{ title: 'Add Lost Reason' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="reason"
					label="Lost Reason"
					name="reason"
					type="select"
					:options="lostReasonOptions"
				/>
				<FormControl
					v-if="reason === 'Other'"
					v-model="other_reason"
					label="Other Reason (specify)"
					type="textarea"
					name="other_reason"
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
import { ref, defineEmits, computed } from 'vue';

const emit = defineEmits(['update']);
const show = defineModel();
const props = defineProps({
	lead_id: {
		type: String,
		required: true,
	},
});

const reason = ref();
const other_reason = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'Lost',
			lost_reason: reason.value,
			other_reason: other_reason.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});

const _lostReasonOptions = [
	'Lost to Competitor',
	'No Response',
	'Budget Constraints',
	'Partner Rejected',
	'Trash Lead',
	'Free User',
	'Not Interested Anymore',
	'Other',
];

const lostReasonOptions = computed(() => {
	return _lostReasonOptions.map((reason) => ({
		label: reason,
		value: reason,
	}));
});
</script>
