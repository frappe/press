<template>
	<ListItem
		class="border-t"
		title="Delete Account and Data"
		:subtitle="subtitle"
	>
		<template #actions>
			<Button
				v-if="!inProgress"
				@click="showDialog = true"
				:label="pending ? 'Resend Email' : 'Delete'"
				:class="{ 'text-red-600': !pending }"
			/>
		</template>
	</ListItem>

	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Delete Account and Data',
			actions: [
				{
					label: 'Send Confirmation Email',
					variant: 'solid',
					theme: 'red',
					loading: deletionRequest.loading,
					onClick: () => deletionRequest.submit(),
				},
			],
		}"
	>
		<template #body-content>
			<div class="prose text-base">
				This permanently deletes your Frappe Cloud account and the personal
				data of your team. You cannot undo it.
				<ul>
					<li>Drop all your sites first.</li>
					<li>Pay all unpaid invoices first.</li>
					<li>
						We send a confirmation email to the team owner. The deletion
						starts only after you open the link in that email.
					</li>
				</ul>
			</div>
			<ErrorMessage class="mt-2" :message="deletionRequest.error" />
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

const showDialog = ref(false)

const status = createResource({
	url: 'press.api.account.team_deletion_status',
	auto: true,
})

const pending = computed(() => status.data === 'Pending Verification')
const inProgress = computed(() =>
	['Deletion Verified', 'Processing Deletion', 'Deleted'].includes(
		status.data,
	),
)

const subtitle = computed(() => {
	if (pending.value)
		return 'We sent a confirmation email. Open the link in it to continue.'
	if (inProgress.value) return 'The deletion of your account is in progress.'
	return 'Permanently delete your account and personal data'
})

const deletionRequest = createResource({
	url: 'press.api.account.request_team_deletion',
	onSuccess() {
		showDialog.value = false
		toast.success('We sent a confirmation email to the team owner')
		status.reload()
	},
})
</script>
