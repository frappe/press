<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import Eligibility from '@/onboarding/modal/Eligibility.vue'
import FrappePartnerships from '@/onboarding/modal/FrappePartnerships.vue'
import PartnerBenefits from '@/onboarding/modal/PartnerBenefits.vue'
import PartnerPlans from '@/onboarding/modal/PartnerPlans.vue'
import PartnerRegistration from '@/onboarding/modal/PartnerRegistration.vue'
import PostRegistrationMessage from '@/onboarding/modal/PostRegistrationMessage.vue'
import SidebarItem from '@/onboarding/modal/SidebarItem.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideXIcon from '~icons/lucide/x'

const open = defineModel<boolean>({ default: false })
const registered = ref(false)
const router = useRouter()
const onboarding = usePartnerOnboarding(inject('team') as any)

const partnerOnboardingSteps = [
	{
		id: 0,
		title: 'Frappe partnerships',
		component: FrappePartnerships,
	},
	{
		id: 1,
		title: 'Benefits',
		component: PartnerBenefits,
	},
	{
		id: 2,
		title: 'Eligibility',
		component: Eligibility,
	},
	{
		id: 3,
		title: 'Tiers',
		component: PartnerPlans,
	},
	{
		id: 4,
		title: 'Registration',
		component: PartnerRegistration,
	},
]

const currentStep = ref(partnerOnboardingSteps[0])

const isLastStep = computed(
	() => currentStep.value.id === partnerOnboardingSteps.length - 1,
)

const nextStep = () => {
	if (!isLastStep.value) {
		currentStep.value = partnerOnboardingSteps[currentStep.value.id + 1]
	}
}

const previousStep = () => {
	if (currentStep.value.id > 0) {
		currentStep.value = partnerOnboardingSteps[currentStep.value.id - 1]
	}
}

const onRegistered = () => {
	registered.value = true
}

// The record now exists — close the modal and take the user to the full
// onboarding workflow. If they are already on that page this is a no-op.
const onContinue = () => {
	open.value = false
	if (router.currentRoute.value.name !== 'Partner Onboarding') {
		router.push('/partner-onboarding')
	}
}
</script>

<template>
	<Dialog
		v-model="open"
		:disable-outside-click-to-close="true"
		size="4xl"
		title="Interested in partnering with us?"
	>
		<template #body>
			<div class="flex min-h-[480px]">
				<!-- hide sidebar if registered -->
				<div
					v-if="!registered"
					class="flex w-[240px] shrink-0 flex-col gap-0.5 rounded-l-xl bg-surface-gray-1 p-3"
				>
					<SidebarItem
						v-for="step in partnerOnboardingSteps"
						:key="step.id"
						:title="step.title"
						:active="currentStep.id === step.id"
						@click="currentStep = step"
					/>
				</div>

				<!-- Main content -->
				<div class="flex flex-1 flex-col p-6">
					<!-- Header -->
					<div
						class="mb-6 flex items-center justify-between"
						v-if="!registered"
					>
						<h3 class="text-4xl-semibold text-ink-gray-8">
							Interested in partnering with us?
						</h3>
						<button
							class="rounded-md p-1 text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
							@click="open = false"
						>
							<LucideXIcon class="h-4 w-4" />
						</button>
					</div>

					<!-- Step content -->
					<div
						class="-m-2 flex-1 overflow-y-auto p-2"
						:class="registered ? 'flex justify-center items-center' : ''"
					>
						<PostRegistrationMessage v-if="registered" @continue="onContinue" />
						<component
							v-else
							:is="currentStep.component"
							@registered="onRegistered"
						/>
					</div>

					<!-- Footer (hidden after registration) -->
					<div
						v-if="!registered"
						class="mt-8 flex items-center justify-between"
					>
						<Button
							variant="outline"
							link="https://docs.frappe.io/partner-guide/why-partner"
							>Learn more</Button
						>
						<div class="flex items-center gap-2">
							<Button
								v-if="currentStep.id > 0"
								variant="subtle"
								@click="previousStep"
							>
								Back
							</Button>
							<Button v-if="!isLastStep" variant="solid" @click="nextStep">
								Next
							</Button>
							<Button
								v-if="isLastStep"
								variant="solid"
								type="submit"
								form="registration-form"
								:loading="onboarding.saving.value"
							>
								Register as a partner
							</Button>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
