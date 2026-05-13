<template>
	<Dialog v-model="show" :options="{ title: 'Budget Alerts' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<Switch
					v-model="receiveBudgetAlerts"
					label="Enable Budget Alerts"
					:description="`Receive an email alert when monthly spend exceeds limit`"
				/>
				<div v-if="receiveBudgetAlerts">
					<FormControl
						v-model="monthlyAlertLimit"
						:label="`Monthly Alert Limit (${team?.doc?.currency})`"
						:placeholder="`Enter amount in ${team?.doc?.currency}`"
						type="number"
						:min="0"
						:step="1000"
					/>
				</div>
				<ErrorMessage class="mt-2" :message="errorMessage" />
				<Button
					class="w-full mt-4"
					variant="solid"
					label="Save"
					:loading="team.setValue.loading"
					@click="saveSettings"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import { Dialog, Switch, Button, ErrorMessage, FormControl } from 'frappe-ui';
import { ref, inject } from 'vue';

const props = defineProps({
	showMessage: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(['success']);
const show = defineModel();

const team = inject('team');

let errorMessage = ref('');

const receiveBudgetAlerts = ref(Boolean(team?.doc?.receive_budget_alerts));
const monthlyAlertLimit = ref(team?.doc?.monthly_alert_threshold || '');

const saveSettings = async () => {
	try {
		// Check if no changes were made
		const currentAlerts = !!team.doc.receive_budget_alerts;
		const currentLimit = team.doc.monthly_alert_threshold || 0;
		const newLimit = receiveBudgetAlerts.value
			? parseFloat(monthlyAlertLimit.value) || 0
			: 0;

		// If saved without any changes, just close the dialog
		if (
			receiveBudgetAlerts.value === currentAlerts &&
			newLimit === currentLimit
		) {
			show.value = false;
			return;
		}

		// Validate monthly limit if budget alerts are enabled
		if (receiveBudgetAlerts.value) {
			const numValue = parseFloat(monthlyAlertLimit.value);
			if (isNaN(numValue) || numValue <= 0) {
				errorMessage.value = 'Please enter a valid positive amount';
				return;
			}

			// Update both fields
			await team.setValue.submit({
				receive_budget_alerts: true,
				monthly_alert_threshold: numValue,
			});
		} else {
			// Disable alerts and clear limit
			await team.setValue.submit({
				receive_budget_alerts: false,
				monthly_alert_threshold: 0,
			});
		}

		emit('success');
		show.value = false;
	} catch (error) {
		console.error('Error saving budget alert settings:', error);
		errorMessage.value =
			'An error occurred while saving settings. Please try again.';
	}
};
</script>
