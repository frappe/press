<script setup lang="ts">
import { Avatar, Badge, Button, Tooltip } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import UnregisterButton from '@/onboarding/onboardingRightContainer/UnregisterButton.vue'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'
import LucideLogOut from '~icons/lucide/log-out'

const team = inject('team')
const onboarding = usePartnerOnboarding(team as any)
const openUnregisterConfirmationDialog = ref(false)

const companyName = computed(() => {
	return (
		onboarding.doc.value?.company_name ||
		onboarding.form.company_name ||
		(team as any)?.doc?.company_name ||
		(team as any)?.doc?.billing_name ||
		'Company Name'
	)
})

const companyInitial = computed(() => companyName.value.trim().charAt(0))

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

// only show tooltip when the company name is truncated
const showTooltip = computed(() => {
	return companyName.value.length > 20
})
</script>

<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center gap-3">
			<Avatar :label="companyInitial" size="lg" class="shrink-0" />
			<div class="min-w-0 flex-1">
				<Tooltip v-if="showTooltip" :text="companyName">
					<p
						class="truncate text-p-base font-semibold text-ink-gray-9 cursor-default"
					>
						{{ companyName }}
					</p>
				</Tooltip>
				<p
					v-else
					class="text-p-base font-semibold text-ink-gray-9 cursor-default"
				>
					{{ companyName }}
				</p>
				<div class="mt-1 flex items-center gap-2">
					<span class="text-p-sm text-ink-gray-5">Partner application</span>
					<Badge variant="subtle" :theme="statusTheme" size="sm">
						{{ statusLabel }}
					</Badge>
				</div>
			</div>
		</div>

		<Button
			v-if="onboarding.isRegistered.value"
			class="w-full"
			size="md"
			variant="outline"
			theme="red"
			label="Unregister"
			@click="openUnregisterConfirmationDialog = true"
		>
			<template #prefix>
				<LucideLogOut class="size-4" />
			</template>
		</Button>

		<UnregisterButton v-model="openUnregisterConfirmationDialog" />
	</div>
</template>
