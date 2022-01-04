<template>
	<Card
		title="Email Notifications"
		subtitle="Email preferences for your account"
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
		<Dialog title="Edit Emails" v-model="showEmailsEditDialog">
			<div class="mt-3" v-for="email in emailData" :key="email.type">
				<Input
					:label="fieldLabelMap[email.type] || email.type"
					type="text"
					v-model="email.value"
				/>
			</div>
			<ErrorMessage class="mt-2" :error="$resources.changeEmail.error" />
			<template #actions>
				<Button class="mr-3" @click="showEmailsEditDialog = false"
					>Cancel</Button
				>
				<Button type="primary" @click="$resources.changeEmail.submit()">
					Save Changes
				</Button>
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountEmails',
	resources: {
		getEmails() {
			return {
				method: 'press.api.account.get_emails',
				auto: true,
				onSuccess(res) {
					this.emailData = res;
				}
			};
		},
		changeEmail() {
			return {
				method: 'press.api.account.update_emails',
				params: {
					data: JSON.stringify(this.emailData)
				},
				onSuccess(res) {
					this.showEmailsEditDialog = false;
				}
			};
		}
	},
	data() {
		return {
			showEmailsEditDialog: false,
			emailData: []
		};
	},
	computed: {
		fieldLabelMap() {
			return {
				invoices: 'Email To Recieve Invoices',
				marketplace_notifications: 'Marketplace Notifications'
			};
		}
	}
};
</script>
