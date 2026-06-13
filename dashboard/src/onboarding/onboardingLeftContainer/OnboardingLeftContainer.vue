<script setup>
import PartnerOnboardingStepsAccordion from '@/onboarding/onboardingLeftContainer/PartnerOnboardingStepsAccordion.vue'
</script>

<template>
	<!-- Main column: align with header (px-5 on page), fill space until sidebar -->
	<div class="min-w-0 flex-1 overflow-auto px-12 w-full max-w-7xl mx-auto">
		<div class="flex flex-col pt-2 flex-1 gap-6">
			<p class="text-xl font-semibold text-ink-gray-9 text-left">
				Your journey to becoming a Frappe partner
			</p>
			<PartnerOnboardingStepsAccordion />
		</div>
	</div>
</template>
