<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Add New Member',
			actions: [
				{
					label: 'Send Invitation',
					variant: 'solid',
					loading: addMember.loading,
					onClick: () => addMember.submit({ email: memberEmail })
				}
			]
		}"
	>
		<template v-slot:body-content>
			<FormControl
				label="Enter the email address of your teammate to invite them."
				class="mt-2"
				v-model="memberEmail"
				placeholder="Email Address"
				required
			/>
			<ErrorMessage :message="addMember.error?.message" />
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import { ref } from 'vue';
import { getTeam } from '../../data/team';
import { toast } from 'vue-sonner';

const emit = defineEmits(['memberAdded']);

const showDialog = ref(true);
const memberEmail = ref('');

const addMember = createResource({
	url: 'press.api.client.run_doc_method',
	makeParams() {
		return {
			dt: 'Team',
			dn: getTeam().doc.name,
			method: 'invite_team_member',
			args: {
				email: memberEmail.value
			}
		};
	},
	onSuccess() {
		showDialog.value = false;
		memberEmail.value = null;
		toast.success('Invite Sent!');
		emit('memberAdded');
	}
});
</script>
