<template>
	<Dialog v-model="show" :options="{ title: 'Transfer Credits' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<p class="text-p-base text-ink-gray-7">
					Credits go to the account that owns the email address you enter. Only
					credits you have paid for can be transferred, and both accounts must
					be billed in {{ team.doc.currency }}.
				</p>
				<FormControl
					v-model="recipientEmail"
					label="Recipient's email"
					type="email"
					placeholder="jane@example.com"
					autocomplete="off"
				/>
				<div>
					<FormControl
						v-model="amount"
						:label="`Amount (${team.doc.currency})`"
						type="number"
						min="0"
						placeholder="0.00"
						autocomplete="off"
					/>
					<div class="mt-1.5 text-sm text-ink-gray-6">
						{{ userCurrency(transferableCredits.data?.message || 0) }} available
						to transfer
					</div>
				</div>
				<ErrorMessage :message="team.transferCredits.error" />
				<Button
					class="w-full"
					variant="solid"
					label="Transfer"
					:loading="team.transferCredits.loading"
					@click="transfer"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	Button,
	ErrorMessage,
	FormControl,
	createResource,
} from 'frappe-ui';
import { ref, inject } from 'vue';
import { toast } from 'vue-sonner';
import { userCurrency } from '../../utils/format';

const emit = defineEmits(['success']);
const show = defineModel();

const team = inject('team');

const recipientEmail = ref('');
const amount = ref('');

const transferableCredits = createResource({
	url: 'press.api.client.run_doc_method',
	params: {
		dt: 'Team',
		dn: team.name,
		method: 'get_transferable_credits',
	},
	auto: true,
});

async function transfer() {
	if (team.transferCredits.loading) return;
	try {
		await team.transferCredits.submit({
			amount: amount.value,
			recipient_email: recipientEmail.value,
		});
	} catch (error) {
		return; // shown inline by ErrorMessage
	}
	show.value = false;
	toast.success('Credits transferred');
	emit('success');
}
</script>
