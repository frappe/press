<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { showOnboardingToast } from '@/onboarding/toast'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideMail from '~icons/lucide/mail'
import LucideX from '~icons/lucide/x'

const open = defineModel({ default: false })

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const resendingRequest = ref('')

const linkRequests = computed(
	() => onboarding.certificateStatus.value.link_requests || [],
)
const linkedCertificates = computed(() => {
	const requestKeys = new Set(
		linkRequests.value.map(
			(request) => `${request.user_email.toLowerCase()}:${request.course}`,
		),
	)

	return (onboarding.certificateStatus.value.linked_certificates || []).filter(
		(certificate) =>
			!requestKeys.has(
				`${certificate.user_email.toLowerCase()}:${certificate.course}`,
			),
	)
})
const hasRows = computed(
	() => linkedCertificates.value.length > 0 || linkRequests.value.length > 0,
)

const courseLabels: Record<string, string> = {
	'frappe-developer-certification': 'Framework certification',
	'app-development-with-frappe-framework': 'Framework certification',
	'erpnext-distribution': 'ERPNext certification',
	'erpnext-training': 'ERPNext certification',
}

function setOpen(isOpen: boolean) {
	open.value = isOpen
	if (isOpen) {
		onboarding.loadCertificateStatus()
	}
}

function closeModal() {
	setOpen(false)
}

function courseLabel(course: string) {
	return courseLabels[course] || course
}

function statusClass(status: string) {
	if (status === 'Approved') {
		return 'bg-surface-green-2 text-ink-green-6'
	}
	return 'bg-surface-amber-2 text-ink-amber-6'
}

function statusLabel(status: string) {
	return status === 'Approved' ? 'Approved' : 'Approval pending'
}

async function resend(requestName: string) {
	resendingRequest.value = requestName
	try {
		await onboarding.resendCertificateLinkRequest(requestName)
		showOnboardingToast('success', 'Verification email sent')
	} catch (error: any) {
		showOnboardingToast('error', error.messages?.[0] || error.message)
	} finally {
		resendingRequest.value = ''
	}
}
</script>

<template>
	<Dialog
		:model-value="open"
		@update:model-value="setOpen"
		:disable-outside-click-to-close="true"
		size="2xl"
		title="Certification link status"
	>
		<template #body-header>
			<div class="flex items-start justify-between gap-4">
				<h3 class="text-xl-semibold leading-6 text-ink-gray-9">
					Certification link status
				</h3>
				<button
					type="button"
					class="-mr-1 rounded-md p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
					aria-label="Close"
					@click="closeModal"
				>
					<LucideX class="size-5" />
				</button>
			</div>
		</template>

		<div class="-mx-1 max-h-80 overflow-y-auto px-1">
			<div v-if="hasRows" class="divide-y divide-outline-gray-1">
				<div
					v-for="certificate in linkedCertificates"
					:key="certificate.name"
					class="flex items-center justify-between gap-4 py-4"
				>
					<div class="min-w-0">
						<p class="truncate text-p-base-medium text-ink-gray-9">
							{{ certificate.user_email }}
						</p>
						<p class="truncate text-p-sm text-ink-gray-6">
							{{ courseLabel(certificate.course) }}
						</p>
					</div>
					<span
						class="inline-flex shrink-0 items-center rounded bg-surface-green-2 px-2 py-0.5 text-p-sm-medium text-ink-green-6"
					>
						Linked
					</span>
				</div>

				<div
					v-for="request in linkRequests"
					:key="request.name"
					class="flex items-center justify-between gap-4 py-4"
				>
					<div class="min-w-0">
						<p class="truncate text-p-base-medium text-ink-gray-9">
							{{ courseLabel(request.course) }}
						</p>
						<p class="truncate text-p-sm text-ink-gray-6">
							{{ request.user_email }}
						</p>
					</div>
					<div class="flex shrink-0 items-center gap-2">
						<span
							class="inline-flex items-center rounded px-2 py-0.5 text-p-sm-medium"
							:class="statusClass(request.status)"
						>
							{{ statusLabel(request.status) }}
						</span>
						<Button
							v-if="request.status === 'Pending'"
							variant="subtle"
							size="sm"
							label="Resend email"
							:icon-left="LucideMail"
							:loading="resendingRequest === request.name"
							@click="resend(request.name)"
						/>
					</div>
				</div>
			</div>

			<p v-else class="py-6 text-p-base text-ink-gray-6">
				No linked certificates or pending requests found.
			</p>
		</div>
	</Dialog>
</template>
