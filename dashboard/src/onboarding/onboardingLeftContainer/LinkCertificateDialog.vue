<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl } from 'frappe-ui'
import { inject, ref, useTemplateRef, watch } from 'vue'
import EmailInput from '@/components/EmailInput.vue'
import { showOnboardingToast } from '@/onboarding/toast'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideX from '~icons/lucide/x'

const open = defineModel({ default: false })

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)

const certificateType = ref('frappe')
const userEmail = ref('')
const submitted = ref(false)
const submitError = ref('')
const submitting = ref(false)
const emailInputRef = useTemplateRef('emailInputRef')

const courseTypes = [
	{ label: 'Framework', value: 'frappe' },
	{ label: 'ERPNext', value: 'erpnext' },
]

watch(open, (isOpen) => {
	if (isOpen) {
		certificateType.value = 'frappe'
		userEmail.value = ''
		submitted.value = false
		submitError.value = ''
	}
})

watch([certificateType, userEmail], () => {
	submitError.value = ''
})

function getErrorMessage(error: any) {
	return (
		error.messages?.[0] || error.message || 'Could not send verification email.'
	)
}

async function handleSubmit() {
	submitted.value = true
	submitError.value = ''

	if (!emailInputRef.value?.validate()) return

	submitting.value = true
	try {
		const email = userEmail.value.trim()
		const result = await onboarding.sendCertificateLinkRequest({
			user_email: email,
			certificate_type: certificateType.value,
		})

		showOnboardingToast(
			'success',
			result?.status === 'Linked'
				? 'Certificate already linked'
				: 'Validation email sent',
		)
		open.value = false
	} catch (error: any) {
		submitError.value = getErrorMessage(error)
	} finally {
		submitting.value = false
	}
}
</script>

<template>
	<Dialog
		v-model="open"
		:disable-outside-click-to-close="true"
		:options="{ size: 'md' }"
	>
		<template #body-main>
			<form class="bg-surface-modal p-6" @submit.prevent="handleSubmit">
				<div class="flex items-start justify-between gap-4">
					<div>
						<h3 class="text-lg font-semibold leading-6 text-ink-gray-9">
							Link certificate
						</h3>
						<p class="mt-2 text-p-sm leading-5 text-ink-gray-6">
							Send a verification email to the certificate holder. Once they
							approve it, the certificate is linked to your account.
						</p>
					</div>
					<button
						type="button"
						class="-mr-1 rounded-md p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
						aria-label="Close"
						@click="open = false"
					>
						<LucideX class="size-4" />
					</button>
				</div>

				<div class="mt-5">
					<FormControl
						v-model="certificateType"
						label="Certificate Type"
						type="select"
						size="sm"
						variant="outline"
						:options="courseTypes"
					/>
				</div>

				<EmailInput
					v-model="userEmail"
					ref="emailInputRef"
					class="mt-4"
					label="User Email"
					:show-error="submitted"
					required-message="User email is required."
				/>

				<ErrorMessage v-if="submitError" class="mt-4" :message="submitError" />

				<Button
					variant="solid"
					class="mt-6 w-full"
					label="Send verification email"
					:loading="submitting"
					@click="handleSubmit"
				/>
			</form>
		</template>
	</Dialog>
</template>
