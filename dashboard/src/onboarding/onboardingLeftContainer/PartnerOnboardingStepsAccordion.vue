<script setup lang="ts">
import { Button } from 'frappe-ui'
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
	FAccordionContent,
	FAccordionHeader,
	FAccordionItem,
	FAccordionRoot,
	FAccordionTrigger,
} from '@/onboarding/accordion'
import PartnerOnboardingModal from '@/onboarding/modal/PartnerOnboardingModal.vue'
import CertificateLinkStatusDialog from '@/onboarding/onboardingLeftContainer/CertificateLinkStatusDialog.vue'
import LinkCertificateDialog from '@/onboarding/onboardingLeftContainer/LinkCertificateDialog.vue'
import CompanyInformationModal from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationModal.vue'
import { showOnboardingToast } from '@/onboarding/toast'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideCircleDashed from '~icons/lucide/circle-dashed'
import LucideLock from '~icons/lucide/lock'

const openStep = ref('step-profile')
const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const router = useRouter()
const registrationModalOpen = ref(false)
const companyInfoModalOpen = ref(false)
const linkCertificateModalOpen = ref(false)
const certificateStatusModalOpen = ref(false)
const mrrStatusInitialized = ref(false)
let mrrRefreshInterval: ReturnType<typeof setInterval> | null = null

function formatCurrency(amount: number, currency: string) {
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency,
		maximumFractionDigits: 0,
	}).format(amount || 0)
}

const mrrCurrentLabel = computed(() =>
	formatCurrency(
		onboarding.mrrStatus.value.current_amount,
		onboarding.mrrStatus.value.currency,
	),
)
const mrrTargetLabel = computed(() =>
	formatCurrency(
		onboarding.mrrStatus.value.target_amount,
		onboarding.mrrStatus.value.currency,
	),
)
const mrrProgress = computed(() =>
	Math.min(100, Math.max(0, onboarding.mrrStatus.value.progress || 0)),
)

watch(
	() => onboarding.mrrStatus.value.requirement_complete,
	(isComplete, wasComplete) => {
		if (!mrrStatusInitialized.value) {
			mrrStatusInitialized.value = true
			return
		}

		if (isComplete && wasComplete === false) {
			showOnboardingToast('success', 'Minimum MRR achieved')
		}
	},
)

onMounted(async () => {
	await onboarding.loadMRRStatus()
	mrrStatusInitialized.value = true

	mrrRefreshInterval = setInterval(() => {
		onboarding.loadMRRStatus()
	}, 60000)
})

onUnmounted(() => {
	if (mrrRefreshInterval) {
		clearInterval(mrrRefreshInterval)
	}
})

const steps = computed(() => [
	{
		value: 'step-register',
		title: 'Register as a Frappe Partner',
		required: true,
		status: onboarding.isRegistered.value ? 'completed' : 'pending',
		description: null,
		summaryRight: null,
		actionLabel: onboarding.isRegistered.value ? null : 'Register as a partner',
		onClick: () => {
			registrationModalOpen.value = true
		},
	},
	{
		value: 'step-profile',
		title: 'Complete your company profile',
		required: true,
		status: onboarding.isProfileComplete.value ? 'completed' : 'pending',
		description:
			'Before you continue, we need to know more about your company to understand how your company can benefit from becoming a Frappe Partner.',
		summaryRight: null,
		actionLabel: onboarding.isRegistered.value
			? 'Fill out company information'
			: null,
		onClick: () => {
			companyInfoModalOpen.value = true
		},
	},
	{
		value: 'step-certificates',
		title: 'Link at least two Frappe School certificates',
		required: true,
		status: onboarding.isCertificateRequirementComplete.value
			? 'completed'
			: 'pending',
		description:
			'Link two Framework or ERPNext certificates from Frappe School. We will send verification email to each certificate holder to link the certificate.',
		summaryRight: onboarding.isCertificateRequirementComplete.value
			? null
			: `${onboarding.linkedCertificateCount.value} / 2 linked`,
		actionLabel: onboarding.isRegistered.value ? 'Link certificate' : null,
		secondaryActionLabel: onboarding.hasCertificateActivity.value
			? 'Check link status'
			: null,
		onClick: () => {
			onboarding.loadCertificateStatus()
			linkCertificateModalOpen.value = true
		},
		onSecondaryClick: () => {
			onboarding.loadCertificateStatus()
			certificateStatusModalOpen.value = true
		},
	},
	{
		value: 'step-mrr',
		title: `Reach ${mrrTargetLabel.value} MRR on Frappe Cloud`,
		required: true,
		status: onboarding.isMRRRequirementComplete.value ? 'completed' : 'pending',
		description:
			'We track this automatically from customer subscription invoices linked to your partner account. No manual update is needed.',
		summaryRight: onboarding.isMRRRequirementComplete.value
			? null
			: `${mrrCurrentLabel.value} / ${mrrTargetLabel.value}`,
		actionLabel: null,
	},
])

const nextPendingStep = computed(
	() => steps.value.find((step) => step.status !== 'completed')?.value || '',
)

watch(
	nextPendingStep,
	(value) => {
		openStep.value = value
	},
	{ immediate: true },
)

const canSubmit = computed(
	() =>
		onboarding.doc.value?.docstatus === 0 &&
		onboarding.doc.value?.status === 'Draft' &&
		onboarding.isRegistered.value &&
		onboarding.isProfileComplete.value &&
		onboarding.isCertificateRequirementComplete.value &&
		onboarding.isMRRRequirementComplete.value,
)
const isApproved = computed(() => onboarding.doc.value?.status === 'Approved')
const isRejected = computed(() => onboarding.doc.value?.status === 'Rejected')
const submitLabel = computed(() => {
	if (isApproved.value) return 'Become an active partner'
	if (isRejected.value) return 'Start new application'
	if (
		onboarding.doc.value?.docstatus === 1 ||
		onboarding.doc.value?.status === 'Pending Review'
	) {
		return 'Submitted for approval'
	}
	return 'Submit for approval'
})
const submitIcon = computed(() =>
	isApproved.value || isRejected.value ? LucideCircleCheck : LucideLock,
)
const canClickPrimaryAction = computed(
	() => canSubmit.value || isApproved.value || isRejected.value,
)

async function startNewApplication() {
	try {
		await onboarding.unregister()
		showOnboardingToast('success', 'You can start a new application')
	} catch (error: any) {
		showOnboardingToast(
			'error',
			error.messages?.[0] ||
				error.message ||
				'Could not start a new application',
		)
	}
}

async function openPartnerOverview() {
	await (team as any)?.reload?.()
	router.push({ name: 'PartnerOverview' })
}

async function submitForApproval() {
	if (isApproved.value) {
		await openPartnerOverview()
		return
	}

	if (isRejected.value) {
		await startNewApplication()
		return
	}

	try {
		await onboarding.submitForApproval()
		showOnboardingToast('success', 'Details submitted for approval')
	} catch (error: any) {
		showOnboardingToast(
			'error',
			error.messages?.[0] || error.message || 'Could not submit for approval',
		)
	}
}
</script>

<template>
	<div class="flex w-full flex-col gap-6">
		<CompanyInformationModal v-model="companyInfoModalOpen" />
		<PartnerOnboardingModal v-model="registrationModalOpen" />
		<LinkCertificateDialog
			v-if="linkCertificateModalOpen"
			v-model="linkCertificateModalOpen"
		/>
		<CertificateLinkStatusDialog
			v-if="certificateStatusModalOpen"
			v-model="certificateStatusModalOpen"
		/>
		<FAccordionRoot v-model="openStep">
			<FAccordionItem
				v-for="step in steps"
				:key="step.value"
				:value="step.value"
				class="border-b border-outline-gray-modals last:border-b-0"
			>
				<FAccordionHeader>
					<FAccordionTrigger class="py-6">
						<span
							v-if="step.status === 'completed'"
							class="inline-flex shrink-0 text-ink-green-3"
							aria-hidden="true"
						>
							<LucideCircleCheck class="size-4" />
						</span>
						<span
							v-else
							class="inline-flex shrink-0 text-ink-gray-5"
							aria-hidden="true"
						>
							<LucideCircleDashed class="size-4" />
						</span>

						<span class="min-w-0 flex-1">
							<span
								class="text-base font-medium"
								:class="{
									'text-ink-gray-5 line-through': step.status === 'completed',
									'text-ink-gray-8': step.status !== 'completed',
								}"
							>
								{{ step.title }}
								<template v-if="step.required">
									<span class="text-ink-red-4"> *</span>
								</template>
								<template v-else>
									<span class="font-normal text-ink-gray-5"> Optional</span>
								</template>
							</span>
						</span>

						<span
							v-if="step.summaryRight"
							class="shrink-0 whitespace-nowrap pr-2 text-sm font-normal text-ink-gray-6"
						>
							{{ step.summaryRight }}
						</span>

						<LucideChevronDown
							class="size-4 shrink-0 text-ink-gray-6 transition-transform duration-200 group-data-[state=open]:rotate-180"
						/>
					</FAccordionTrigger>
				</FAccordionHeader>

				<FAccordionContent
					v-if="
					step.description || step.actionLabel || step.secondaryActionLabel
				"
				>
					<p
						v-if="step.description"
						class="mb-4 max-w-prose self-stretch text-ink-gray-6 text-p-base font-normal leading-normal tracking-wide"
					>
						{{ step.description }}
					</p>
					<div
						v-if="step.value === 'step-mrr'"
						class="mb-4 flex max-w-prose flex-col gap-2"
					>
						<div class="h-2 overflow-hidden rounded-full bg-surface-gray-2">
							<div
								class="h-full rounded-full bg-surface-gray-7 transition-all"
								:style="{ width: `${mrrProgress}%` }"
							/>
						</div>
						<div
							class="flex items-center justify-between text-sm text-ink-gray-6"
						>
							<span>{{ mrrCurrentLabel }} current MRR</span>
							<span>{{ mrrTargetLabel }} target</span>
						</div>
					</div>
					<Button
						v-if="step.actionLabel"
						variant="solid"
						:label="step.actionLabel"
						@click="step.onClick"
					/>
					<Button
						v-if="step.secondaryActionLabel"
						variant="subtle"
						class="ml-2"
						:label="step.secondaryActionLabel"
						@click="step.onSecondaryClick"
					/>
				</FAccordionContent>
			</FAccordionItem>
		</FAccordionRoot>

		<div
			v-if="isRejected"
			class="max-w-prose rounded border border-outline-gray-2 bg-surface-red-2 p-4"
		>
			<p class="text-p-base font-medium text-ink-red-4">
				Your application was rejected
			</p>
			<p class="mt-1 text-p-base text-ink-gray-7">
				Review the feedback, make the required changes, and start a new
				application when you are ready.
			</p>
			<p
				v-if="onboarding.doc.value?.rejection_reason"
				class="mt-3 whitespace-pre-wrap text-p-base text-ink-gray-8"
			>
				{{ onboarding.doc.value.rejection_reason }}
			</p>
		</div>

		<div class="flex justify-start">
			<Button
				variant="solid"
				class="w-full sm:w-auto"
				:disabled="!canClickPrimaryAction"
				:iconLeft="submitIcon"
				:loading="
					onboarding.submittingForApproval.value || onboarding.unregistering.value
				"
				:label="submitLabel"
				@click="submitForApproval"
			/>
		</div>
	</div>
</template>
