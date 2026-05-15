<script setup>
import { computed, inject, ref, useTemplateRef, watch } from 'vue';
import { Button, Dialog } from 'frappe-ui';
import { toast } from 'vue-sonner';
import LucideX from '~icons/lucide/x';
import CompanyInformationFormFirstStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormFirstStep.vue';
import CompanyInformationFormSecondStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormSecondStep.vue';
import CompanyInformationFormThirdStep from '@/onboarding/onboardingLeftContainer/modal/CompanyInformationFormThirdStep.vue';

const open = defineModel({ default: false });

const team = inject('team');

const totalSteps = 3;

const currentStepIndex = ref(0);
const formStepKey = ref(0);

const step0Ref = useTemplateRef('step0Ref');
const step1Ref = useTemplateRef('step1Ref');
const step2Ref = useTemplateRef('step2Ref');

const stepRefs = [step0Ref, step1Ref, step2Ref];

const displayCompanyName = computed(() => {
	const doc = team?.doc;
	return (
		doc?.company_name?.trim() ||
		doc?.billing_name?.trim() ||
		doc?.team_title?.trim() ||
		'your company'
	);
});

const stepIndicator = computed(
	() => `Step ${currentStepIndex.value + 1}/${totalSteps}`,
);

const primaryLabel = computed(() =>
	currentStepIndex.value === totalSteps - 1 ? 'Submit' : 'Continue',
);

watch(open, (isOpen) => {
	if (isOpen) {
		currentStepIndex.value = 0;
		formStepKey.value += 1;
	}
});

function closeModal() {
	open.value = false;
}

function goBack() {
	if (currentStepIndex.value > 0) {
		currentStepIndex.value -= 1;
	}
}

function onStepContinue() {
	if (currentStepIndex.value < totalSteps - 1) {
		currentStepIndex.value += 1;
	} else {
		handleSubmit();
	}
}

function handlePrimaryClick() {
	const refEl = stepRefs[currentStepIndex.value]?.value;
	if (refEl?.tryContinue) {
		refEl.tryContinue();
	}
}

function handleSubmit() {
	// Hook for persisting all steps once API exists
	toast.success('Company information saved');
	closeModal();
}
</script>

<template>
	<Dialog
		v-model="open"
		:disable-outside-click-to-close="true"
		:options="{
			size: '2xl',
		}"
	>
		<template #title>
			<h2 class="text-xl font-semibold tracking-tight text-ink-gray-9">
				Tell us more about {{ displayCompanyName }}
			</h2>
		</template>
		<template #body>
			<div class="flex max-h-[90vh] flex-col px-1 pb-2 pt-1">
				<div class="mb-4 flex items-start justify-between gap-4">
					<div class="min-w-0 flex-1">
						<p class="text-xs font-medium text-ink-gray-5">
							{{ stepIndicator }}
						</p>

						<div class="mt-4 flex w-full items-center">
							<div
								class="h-2 shrink-0 rounded-l bg-gray-900 transition-[width] duration-200 ease-out"
								:style="{
									width: `${((currentStepIndex + 1) / totalSteps) * 100}%`,
								}"
							/>
							<div class="h-px min-w-0 flex-1 bg-gray-200" />
						</div>
					</div>
					<button
						type="button"
						class="rounded-md p-1.5 text-ink-gray-6 hover:bg-gray-100 hover:text-ink-gray-9"
						aria-label="Close"
						@click="close"
					>
						<LucideX class="size-4" />
					</button>
				</div>

				<div class="-mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-2">
					<CompanyInformationFormFirstStep
						v-show="currentStepIndex === 0"
						:key="formStepKey"
						ref="step0Ref"
						@continue="onStepContinue"
					/>
					<CompanyInformationFormSecondStep
						v-show="currentStepIndex === 1"
						ref="step1Ref"
						@continue="onStepContinue"
					/>
					<CompanyInformationFormThirdStep
						v-show="currentStepIndex === 2"
						ref="step2Ref"
						@continue="onStepContinue"
					/>
				</div>

				<div
					class="mt-4 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row-reverse sm:justify-between"
				>
					<Button
						variant="solid"
						class="w-full sm:w-auto sm:min-w-[140px]"
						:label="primaryLabel"
						@click="handlePrimaryClick"
					/>
					<Button
						v-if="currentStepIndex > 0"
						variant="subtle"
						class="w-full sm:w-auto"
						label="Back"
						@click="goBack"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
