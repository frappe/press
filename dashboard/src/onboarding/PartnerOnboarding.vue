<!-- This is the main partner onboarding page layout-->

<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { inject, onMounted } from 'vue'
import Header from '@/components/Header.vue'
import OnboardingLeftContainer from '@/onboarding/onboardingLeftContainer/OnboardingLeftContainer.vue'
import OnboardingRightSidebarLayout from '@/onboarding/onboardingRightContainer/OnboardingRightSidebarLayout.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)

onMounted(() => {
	onboarding.load()
})
</script>

<template>
	<!-- <PartnerOnboardingModal /> -->
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<Breadcrumbs
					:items="[{ label: 'Partnership', route: { name: 'Partnership' } }]"
				/>
			</Header>
		</div>

		<div class="flex flex-row gap-6 p-5 h-full">
			<OnboardingLeftContainer />
			<div class="flex w-[280px] shrink-0 flex-col gap-2 h-full">
				<OnboardingRightSidebarLayout />
			</div>
		</div>
	</div>
</template>
