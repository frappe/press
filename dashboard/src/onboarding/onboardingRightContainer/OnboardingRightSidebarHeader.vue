<script setup lang="ts">
import { Avatar, Badge, Button } from 'frappe-ui'
import { computed, inject } from 'vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)

const companyName = computed(() => {
	return (
		onboarding.form.company_name ||
		(team as any)?.doc?.company_name ||
		(team as any)?.doc?.billing_name ||
		'Company Name'
	)
})

const status = computed(() => onboarding.doc.value?.status || 'Inactive')
const statusTheme = computed(() => {
	if (status.value === 'Approved') return 'green'
	if (status.value === 'Submission Pending') return 'gray'
	if (status.value === 'Rejected') return 'red'
	return 'orange'
})
</script>

<template>
	<div class="flex flex-col gap-2">
		<Avatar :label="companyName" size="lg" />
		<p class="text-p-base font-semibold text-ink-gray-8">{{ companyName }}</p>
		<Badge variant="subtle" :theme="statusTheme" size="lg">{{ status }}</Badge>
	</div>
	<div class="flex justify-start items-center">
		<Button variant="subtle" theme="red">Unregister</Button>
	</div>
</template>
