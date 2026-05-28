<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import { showOnboardingToast } from '@/onboarding/toast'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideMail from '~icons/lucide/mail'
import LucideX from '~icons/lucide/x'

const open = defineModel({ default: false })

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const resendingRequest = ref('')

const linkedCertificates = computed(
	() => onboarding.certificateStatus.value.linked_certificates || [],
)
const pendingRequests = computed(
	() => onboarding.certificateStatus.value.pending_requests || [],
)
const hasRows = computed(
	() => linkedCertificates.value.length > 0 || pendingRequests.value.length > 0,
)

const courseLabels: Record<string, string> = {
	'frappe-developer-certification': 'Framework certification',
	'app-development-with-frappe-framework': 'Framework certification',
	'erpnext-distribution': 'ERPNext certification',
	'erpnext-training': 'ERPNext certification',
}

watch(open, (isOpen) => {
	if (isOpen) {
		onboarding.loadCertificateStatus()
	}
})

function closeModal() {
	open.value = false
}

function courseLabel(course: string) {
	return courseLabels[course] || course
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
		v-model="open"
		:disable-outside-click-to-close="true"
		:options="{ size: '2xl', title: 'Certification link status' }"
	>
		<template #body-header>
			<div class="flex items-start justify-between gap-4">
				<h3 class="text-lg font-semibold leading-6 text-ink-gray-9">
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

		<template #body-content>
			<div class="-mx-1 max-h-80 overflow-y-auto px-1">
				<div v-if="hasRows" class="divide-y divide-outline-gray-1">
					<div
						v-for="certificate in linkedCertificates"
						:key="certificate.name"
						class="flex items-center justify-between gap-4 py-4"
					>
						<div class="min-w-0">
							<p class="truncate text-p-base font-medium text-ink-gray-9">
								{{ certificate.user_email }}
							</p>
							<p class="truncate text-p-sm text-ink-gray-6">
								{{ courseLabel(certificate.course) }}
							</p>
						</div>
						<span
							class="inline-flex shrink-0 items-center rounded bg-surface-green-2 px-2 py-0.5 text-p-sm font-medium text-ink-green-3"
						>
							Linked
						</span>
					</div>

					<div
						v-for="request in pendingRequests"
						:key="request.name"
						class="flex items-center justify-between gap-4 py-4"
					>
						<div class="min-w-0">
							<p class="truncate text-p-base font-medium text-ink-gray-9">
								{{ courseLabel(request.course) }}
							</p>
							<p class="truncate text-p-sm text-ink-gray-6">
								{{ request.user_email }}
							</p>
						</div>
						<div class="flex shrink-0 items-center gap-2">
							<span
								class="inline-flex items-center rounded bg-surface-amber-2 px-2 py-0.5 text-p-sm font-medium text-ink-amber-3"
							>
								Approval pending
							</span>
							<Button
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
		</template>
	</Dialog>
</template>
