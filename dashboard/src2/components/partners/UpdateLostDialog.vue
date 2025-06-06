<template>
	<Dialog v-model="show" :options="{ title: 'Add Lost Reason' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<FormControl
					v-model="reason"
					label="Lost Reason"
					type="textarea"
					name="reason"
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

const reason = ref();
const updateStatus = createResource({
	url: 'press.api.partner.update_lead_status',
	makeParams: () => {
		return {
			lead_name: props.lead_id,
			status: 'Lost',
			lost_reason: reason.value,
		};
	},
	onSuccess: () => {
		emit('update');
		show.value = false;
	},
});
</script>
