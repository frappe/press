<template>
	<Card
		v-if="$team.doc.user === $session.user"
		title="Email Notifications"
		class="mx-auto max-w-3xl"
	>
		<template #actions>
			<Button icon-left="edit" @click="showEmailsEditDialog = true">
				Edit
			</Button>
		</template>
		<ListItem
			v-if="emailData"
			v-for="email in emailData"
			:title="fieldLabelMap[email.type] || email.type"
			:description="email.value"
			:key="email.type"
		>
		</ListItem>
		<Dialog
			:options="{
				title: 'Edit Emails',
				actions: [
					{
						label: 'Save Changes',
						variant: 'solid',
						onClick: () => $resources.changeEmail.submit()
					}
				]
			}"
			v-model="showEmailsEditDialog"
		>
			<template v-slot:body-content>
				<div class="mt-3" v-for="email in emailData" :key="email.type">
					<FormControl
						:label="fieldLabelMap[email.type] || email.type"
						v-model="email.value"
					/>
				</div>
				<ErrorMessage class="mt-2" :message="$resources.changeEmail.error" />
			</template>
		</Dialog>
	</Card>
</template>

<script>
import { toast } from 'vue-sonner';
export default {
	name: 'AccountEmails',
	data() {
		return {
			showEmailsEditDialog: false,
			emailData: []
		};
	},
	resources: {
		getEmails() {
			return {
				url: 'press.api.account.get_emails',
				auto: true,
				transform(data) {
					this.emailData = data.map(d => ({
						type: d.type,
						value: d.value
					}));
				}
			};
		},
		changeEmail() {
			return {
				url: 'press.api.account.update_emails',
				params: {
					data: JSON.stringify(this.emailData)
				},
				onSuccess(res) {
					this.showEmailsEditDialog = false;
					toast.success('Emails updated successfully');
				}
			};
		}
	},
	computed: {
		fieldLabelMap() {
			return {
				billing_email: 'Get billing emails at',
				notify_email: 'Get operational emails at'
			};
		}
	}
};
</script>
