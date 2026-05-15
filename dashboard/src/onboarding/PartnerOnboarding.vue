<!-- This is the main partner onboarding page layout-->

<script setup>
import Header from '@/components/Header.vue';
import OnboardingRightSidebarLayout from '@/onboarding/onboardingRightContainer/OnboardingRightSidebarLayout.vue';
import OnboardingLeftContainer from '@/onboarding/onboardingLeftContainer/OnboardingLeftContainer.vue';
import { Breadcrumbs } from 'frappe-ui';
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
