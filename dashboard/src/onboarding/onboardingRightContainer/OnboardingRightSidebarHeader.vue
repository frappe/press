<script setup lang="ts">
import { Avatar, Badge, Button } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import UnregisterButton from '@/onboarding/onboardingRightContainer/UnregisterButton.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const openUnregisterConfirmationDialog = ref(false)

const companyName = computed(() => {
	return (
		onboarding.form.company_name ||
		(team as any)?.doc?.company_name ||
		(team as any)?.doc?.billing_name ||
		'Company Name'
	)
})

const status = computed(() => onboarding.doc.value?.status || 'Inactive')
const statusLabel = computed(() =>
	status.value === 'Pending Review' ? 'In review' : status.value,
)
const statusTheme = computed(() => {
	if (status.value === 'Approved') return 'green'
	if (status.value === 'Pending Review') return 'gray'
	if (status.value === 'Rejected') return 'red'
	return 'orange'
})
</script>

<template>
	<div class="flex flex-col gap-2">
		<Avatar :label="companyName" size="lg" />
		<p class="text-p-base font-semibold text-ink-gray-8">{{ companyName }}</p>
		<Badge variant="subtle" :theme="statusTheme" size="lg"
			>{{ statusLabel }}</Badge
		>
	</div>
	<div class="flex justify-start items-center">
		<Button
			v-if="onboarding.isRegistered.value"
			variant="subtle"
			theme="red"
			label="Unregister"
			@click="openUnregisterConfirmationDialog = true"
		/>
		<UnregisterButton v-model="openUnregisterConfirmationDialog" />
	</div>
</template>
