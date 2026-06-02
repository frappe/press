<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { computed, inject, reactive, ref, useTemplateRef, watch } from 'vue'
import CompanyInformationFormFirstStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormFirstStep.vue'
import CompanyInformationFormSecondStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormSecondStep.vue'
import CompanyInformationFormThirdStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormThirdStep.vue'
import { showOnboardingToast } from '@/onboarding/toast'
import {
	type PartnerOnboardingDoc,
	usePartnerOnboarding,
} from '@/onboarding/usePartnerOnboarding'
import LucideX from '~icons/lucide/x'

const open = defineModel({ default: false })

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const draft = reactive<PartnerOnboardingDoc>({})

const totalSteps = 3

const currentStepIndex = ref(0)
const formStepKey = ref(0)

const step0Ref = useTemplateRef('step0Ref')
const step1Ref = useTemplateRef('step1Ref')
const step2Ref = useTemplateRef('step2Ref')

const stepRefs = [step0Ref, step1Ref, step2Ref]

const displayCompanyName = computed(() => {
	return (
		draft.company_name?.trim() ||
		onboarding.doc.value?.company_name?.trim() ||
		onboarding.form.company_name?.trim() ||
		'your company'
	)
})

const stepIndicator = computed(
	() => `Step ${currentStepIndex.value + 1}/${totalSteps}`,
)

const primaryLabel = computed(() =>
	currentStepIndex.value === totalSteps - 1 ? 'Save details' : 'Continue',
)

const dialogTitle = computed(
	() => `Tell us more about ${displayCompanyName.value}`,
)

watch(open, (isOpen) => {
	if (isOpen) {
		Object.assign(draft, onboarding.form, onboarding.doc.value || {})
		currentStepIndex.value = 0
		formStepKey.value += 1
	}
})

function closeModal() {
	open.value = false
}

function goBack() {
	if (currentStepIndex.value > 0) {
		currentStepIndex.value -= 1
	}
}

function onStepContinue() {
	if (currentStepIndex.value < totalSteps - 1) {
		currentStepIndex.value += 1
	} else {
		handleSubmit()
	}
}

function handlePrimaryClick() {
	const refEl = stepRefs[currentStepIndex.value]?.value
	if (refEl?.tryContinue) {
		refEl.tryContinue()
	}
}

async function handleSubmit() {
	try {
		Object.assign(onboarding.form, draft)
		await onboarding.save()
		await onboarding.loadMRRStatus()
		showOnboardingToast('success', 'Company details updated')
		closeModal()
	} catch (error: any) {
		showOnboardingToast('error', error.messages?.[0] || error.message)
	}
}
</script>

<template>
	<Dialog
		v-model="open"
		:disable-outside-click-to-close="true"
		:options="{
			size: '2xl',
			title: dialogTitle,
		}"
	>
		<template #body-header>
			<div class="mb-5">
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0">
						<p class="text-sm leading-5 text-ink-gray-6">{{ stepIndicator }}</p>
						<h3
							class="mt-1 truncate text-lg font-semibold leading-6 text-ink-gray-9"
						>
							{{ dialogTitle }}
						</h3>
					</div>
					<button
						type="button"
						class="-mr-1 rounded-md p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
						aria-label="Close"
						@click="closeModal"
					>
						<LucideX class="size-5" />
					</button>
				</div>

				<div class="mt-4 flex w-full items-center">
					<div
						class="h-0.5 shrink-0 bg-ink-gray-9 transition-[width] duration-200 ease-out"
						:style="{
							width: `${((currentStepIndex + 1) / totalSteps) * 100}%`,
						}"
					/>
					<div class="h-px min-w-0 flex-1 bg-outline-gray-1" />
				</div>
			</div>
		</template>

		<template #body-content>
			<div class="-mx-1 max-h-[62vh] min-h-[360px] overflow-y-auto px-1">
				<CompanyInformationFormFirstStep
					v-show="currentStepIndex === 0"
					:key="formStepKey"
					ref="step0Ref"
					:form="draft"
					@continue="onStepContinue"
				/>
				<CompanyInformationFormSecondStep
					v-show="currentStepIndex === 1"
					ref="step1Ref"
					:form="draft"
					@continue="onStepContinue"
				/>
				<CompanyInformationFormThirdStep
					v-show="currentStepIndex === 2"
					ref="step2Ref"
					:form="draft"
					@continue="onStepContinue"
				/>
			</div>
		</template>

		<template #actions>
			<div class="-mx-6 border-t border-outline-gray-1 px-6 pt-4">
				<div
					class="grid gap-2"
					:class="currentStepIndex > 0 ? 'grid-cols-2' : 'grid-cols-1'"
				>
					<Button
						v-if="currentStepIndex > 0"
						variant="subtle"
						class="w-full"
						label="Back"
						@click="goBack"
					/>
					<Button
						variant="solid"
						class="w-full"
						:label="primaryLabel"
						:loading="onboarding.saving.value"
						@click="handlePrimaryClick"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
