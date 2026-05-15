<script setup>
import OnboardingRightSidebarHeader from '@/onboarding/onboardingRightContainer/OnboardingRightSidebarHeader.vue';

const resources = [
	{
		title: 'Benefits of becoming a partner',
		link: '',
	},
	{
		title: 'Partner program guide',
		link: '',
	},
	{
		title: 'Certifications guide',
		link: '',
	},
	{
		title: 'Getting started with Frappe Cloud',
		link: '',
	},
	{
		title: 'Partnership tiers guide',
		link: '',
	},
];
</script>

<template>
	<div class="flex flex-col gap-4 p-4 rounded-md border border-outline-gray-1">
		<OnboardingRightSidebarHeader />
	</div>
	<div
		class="flex flex-col gap-4 p-2 h-full rounded-md border border-outline-gray-1"
	>
		<!-- Title: Resources -->
		<div class="flex items-center gap-2.5 self-stretch p-2">
			<p class="text-p-sm font-medium text-ink-gray-5">Resources</p>
		</div>

		<div
			v-for="(resource, index) in resources"
			:key="resource.title"
			class="flex flex-col items-start gap-1 p-2 border-b border-outline-gray-1"
			:class="{ 'border-b-0': index === resources.length - 1 }"
		>
			<a
				:href="resource.link"
				target="_blank"
				class="text-p-base text-ink-gray-8 leading-normal tracking-wide"
			>
				{{ resource.title }}
			</a>
		</div>
	</div>
</template>
