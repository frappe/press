<script setup>
import { computed, inject } from 'vue'
import CashIcon from '@/components/icons/CashIcon.vue'
import CertifiedIcon from '@/components/icons/Certified.vue'
import {
	getPartnerMRRTargetLabel,
	usePartnerOnboarding,
} from '@/onboarding/usePartnerOnboarding'

const team = inject('team')
const onboarding = usePartnerOnboarding(team)
const mrrTargetLabel = computed(() =>
	getPartnerMRRTargetLabel(onboarding.form.registered_country),
)

const eligibilityCriteria = computed(() => [
	{
		title: 'At least two certified team members',
		description:
			'Partners must have at least two full-time team members who are certified in ERPNext or the Frappe Framework through',
		link: { text: 'Frappe School.', url: 'https://school.frappe.io/home' },
		icon: CertifiedIcon,
	},
	{
		title: `Minimum ${mrrTargetLabel.value} MRR on Frappe Cloud`,
		description:
			'Host client sites with Frappe apps on Frappe Cloud consistently to get started.',
		icon: CashIcon,
	},
])
</script>
<template>
	<p class="text-p-base text-ink-gray-6 mb-4">
		Fulfill the following eligibility criteria to become a partner
	</p>

	<ul
		class="list-none list-inside"
		v-for="eligibility in eligibilityCriteria"
		:key="eligibility.title"
	>
		<li class="flex items-start gap-3 self-stretch mb-4">
			<component :is="eligibility.icon" class="w-5 h-5" />
			<div class="flex flex-col gap-1 items-start flex-1">
				<p class="text-p-base-medium text-ink-gray-8">
					{{ eligibility.title }}
				</p>
				<p class="text-p-base text-ink-gray-6">
					{{ eligibility.description }}
					<a
						v-if="eligibility.link"
						:href="eligibility.link.url"
						target="_blank"
						class="underline"
					>
						{{ eligibility.link.text }}
					</a>
				</p>
			</div>
		</li>
	</ul>
</template>

<style scoped></style>
