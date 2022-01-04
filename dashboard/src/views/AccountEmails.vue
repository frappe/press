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
			v-for="email in $resources.getEmails.data"
			:title="fieldLabelMap[email.type] || email.type"
			:description="email.value"
			:key="email.type"
		>
		</ListItem>
		<Dialog title="Edit Emails" v-model="showEmailsEditDialog">
			<div
				class="mt-3"
				v-for="email in $resources.getEmails.data"
				:key="email.type"
			>
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
				auto: true
			};
		},
		changeEmail() {
			return {
				method: 'press.api.account.update_emails',
				params: {
					data: JSON.stringify(this.$resources.getEmails.data)
				},
				onSuccess(res) {
					this.showEmailsEditDialog = false;
				}
			};
		}
	},
	data() {
		return {
			showEmailsEditDialog: false
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
