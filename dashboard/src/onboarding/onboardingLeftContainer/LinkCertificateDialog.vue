<script setup lang="ts">
import { Button, Dialog, ErrorMessage } from 'frappe-ui'
import { inject, ref, useTemplateRef } from 'vue'
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

const FrappeFrameworkLogo = new URL(
	'../../assets/frappe-framework-logo-og.png',
	import.meta.url,
).href
const ERPNextLogo = new URL(
	'../../assets/erpnext-logo-blue.png',
	import.meta.url,
).href

const certificateTypes = [
	{
		label: 'Frappe Framework',
		value: 'frappe',
		logo: FrappeFrameworkLogo,
	},
	{
		label: 'ERPNext',
		value: 'erpnext',
		logo: ERPNextLogo,
	},
]

function resetForm() {
	certificateType.value = 'frappe'
	userEmail.value = ''
	submitted.value = false
	submitError.value = ''
}

function setOpen(isOpen: boolean) {
	open.value = isOpen
	if (isOpen) {
		resetForm()
		onboarding.loadCertificateStatus()
	}
}

function selectCertificateType(type: string) {
	certificateType.value = type
	submitError.value = ''
}

function setUserEmail(email: string) {
	userEmail.value = email
	submitError.value = ''
}

function getErrorMessage(error: any) {
	return (
		error.messages?.[0] || error.message || 'Could not send verification email.'
	)
}

async function handleSubmit() {
	submitted.value = true
	submitError.value = ''

	if (!emailInputRef.value?.validate()) return

	if (
		onboarding.hasPendingCertificateRequest(
			userEmail.value,
			certificateType.value,
		)
	) {
		submitError.value = 'Verification email already sent to this email.'
		return
	}

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
		setOpen(false)
	} catch (error: any) {
		submitError.value = getErrorMessage(error)
	} finally {
		submitting.value = false
	}
}
</script>

<template>
	<Dialog
		:model-value="open"
		@update:model-value="setOpen"
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
						<p class="mt-1.5 text-p-sm leading-5 text-ink-gray-6">
							Choose a certificate and email the holder for verification.
						</p>
					</div>
					<button
						type="button"
						class="-mr-1 rounded-md p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
						aria-label="Close"
						@click="setOpen(false)"
					>
						<LucideX class="size-4" />
					</button>
				</div>

				<div class="mt-5">
					<label class="text-p-sm text-ink-gray-6">Certificate type</label>
					<div class="mt-2 grid grid-cols-2 gap-2">
						<button
							v-for="type in certificateTypes"
							:key="type.value"
							type="button"
							class="flex min-w-0 items-center gap-2 rounded-md border px-3 py-2.5 text-left transition-colors"
							:class="certificateType === type.value
								? 'border-outline-gray-4 bg-surface-gray-1 shadow-sm'
								: 'border-outline-gray-2 bg-surface-white hover:border-outline-gray-3 hover:bg-surface-gray-1'
								"
							:aria-pressed="certificateType === type.value"
							@click="selectCertificateType(type.value)"
						>
							<span
								class="grid size-7 shrink-0 place-items-center overflow-hidden rounded bg-surface-white"
							>
								<img :src="type.logo" :alt="type.label" class="size-5" />
							</span>
							<span class="truncate text-p-sm font-medium text-ink-gray-8">
								{{ type.label }}
							</span>
						</button>
					</div>
				</div>

				<EmailInput
					:model-value="userEmail"
					@update:model-value="setUserEmail"
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
