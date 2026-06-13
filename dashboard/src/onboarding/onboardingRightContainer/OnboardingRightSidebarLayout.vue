<script setup>
import OnboardingRightSidebarHeader from '@/onboarding/onboardingRightContainer/OnboardingRightSidebarHeader.vue'

const resources = [
	{
		title: 'Benefits of becoming a partner',
		link: 'https://docs.frappe.io/partner-guide/why-partner',
	},
	{
		title: 'Partner program guide',
		link: 'https://docs.frappe.io/partner-guide/guide-for-new-partners',
	},
	{
		title: 'Certifications guide',
		link: 'https://docs.frappe.io/school/partner-certification',
	},
	{
		title: 'Getting started with Frappe Cloud',
		link: 'https://frappe.io/cloud',
	},
	{
		title: 'Partnership tiers guide',
		link: 'https://frappe.io/partners/plans',
	},
]
</script>

<template>
	<div class="rounded-lg border border-outline-gray-1 bg-surface-base p-4">
		<OnboardingRightSidebarHeader />
	</div>
	<div
		class="flex h-full flex-col overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-base"
	>
		<!-- Title: Resources -->
		<div class="px-4 py-3">
			<p class="text-p-sm-medium text-ink-gray-5">Resources</p>
		</div>

		<div class="px-1.5">
			<div
				v-for="(resource, index) in resources"
				:key="resource.title"
				class="border-b border-outline-gray-1 px-4 py-3 transition-colors hover:bg-surface-gray-1"
				:class="{ 'border-b-0': index === resources.length - 1 }"
			>
				<a
					:href="resource.link"
					target="_blank"
					class="block text-p-sm leading-5 text-ink-gray-8"
				>
					{{ resource.title }}
				</a>
			</div>
		</div>
	</div>
</template>
