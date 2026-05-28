<script setup lang="ts">
import { Button } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
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
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideCircleDashed from '~icons/lucide/circle-dashed'
import LucideLock from '~icons/lucide/lock'

const openStep = ref('step-profile')
const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const registrationModalOpen = ref(false)
const companyInfoModalOpen = ref(false)
const linkCertificateModalOpen = ref(false)
const certificateStatusModalOpen = ref(false)

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
			'Link two Framework or ERPNext certificates from Frappe School. We will send approval email to each certificate holder to link the certificate.',
		summaryRight: onboarding.isCertificateRequirementComplete.value
			? null
			: `${onboarding.linkedCertificateCount.value} / 2 linked`,
		actionLabel: onboarding.isRegistered.value ? 'Link certificate' : null,
		secondaryActionLabel: onboarding.hasCertificateActivity.value
			? 'Check link status'
			: null,
		onClick: () => {
			linkCertificateModalOpen.value = true
		},
		onSecondaryClick: () => {
			certificateStatusModalOpen.value = true
		},
	},
	{
		value: 'step-mrr',
		title: 'Log an MRR of at least $100 on Frappe Cloud',
		required: true,
		status: 'pending',
		description:
			'Create sites and manage hosting for your customers that use Frappe apps on Frappe Cloud consistently to cross this threshold. Based on your Billing details, we will automatically update this step’s completion.',
		summaryRight: null,
		actionLabel: null,
	},
])

const canSubmit = computed(() => false)
</script>

<template>
	<div class="flex w-full flex-col gap-6">
		<CompanyInformationModal v-model="companyInfoModalOpen" />
		<PartnerOnboardingModal v-model="registrationModalOpen" />
		<LinkCertificateDialog v-model="linkCertificateModalOpen" />
		<CertificateLinkStatusDialog v-model="certificateStatusModalOpen" />
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

		<div class="flex justify-start">
			<Button
				variant="solid"
				class="w-full sm:w-auto"
				:disabled="!canSubmit"
				:iconLeft="LucideLock"
				:loading="onboarding.saving.value"
				label="Submit for approval"
			/>
		</div>
	</div>
</template>
