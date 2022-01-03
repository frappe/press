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
			v-for="email in $resources.emails.data"
			:title="email.type"
			:description="email.value"
			:key="email.type"
		>
		</ListItem>
		<Dialog title="Edit Emails" v-model="showEmailsEditDialog">
			<div
				class="mt-3"
				v-for="email in $resources.emails.data"
				:key="email.type"
			>
				<Input :label="email.type" type="text" v-model="email.value" />
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
		emails() {
			return {
				method: 'press.api.account.get_emails',
				auto: true
			};
		},
		changeEmail() {
			return {
				method: 'press.api.account.update_emails',
				params: {
					data: JSON.stringify(this.$resources.emails.data)
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
	}
};
</script>
