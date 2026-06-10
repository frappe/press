<script setup lang="ts">
import { Avatar, Badge, Tooltip } from 'frappe-ui'
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
</script>

<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center gap-3">
			<Avatar :label="companyInitial" size="lg" class="shrink-0" />
			<div class="min-w-0 flex-1">
				<Tooltip :text="companyName">
					<p
						class="truncate text-p-base font-semibold text-ink-gray-9 cursor-default"
					>
						{{ companyName }}
					</p>
				</Tooltip>
				<div class="mt-1 flex items-center gap-2">
					<span class="text-p-sm text-ink-gray-5">Partner application</span>
					<Badge variant="subtle" :theme="statusTheme" size="sm">
						{{ statusLabel }}
					</Badge>
				</div>
			</div>
		</div>

		<button
			v-if="onboarding.isRegistered.value"
			type="button"
			class="group flex w-full items-center justify-center gap-1.5 rounded-md border border-outline-gray-2 px-3 py-2 text-p-sm text-ink-gray-6 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-1 hover:text-ink-red-4"
			@click="openUnregisterConfirmationDialog = true"
		>
			<LucideLogOut
				class="size-3.5 text-ink-gray-5 transition-colors group-hover:text-ink-red-4"
			/>
			Unregister
		</button>

		<UnregisterButton v-model="openUnregisterConfirmationDialog" />
	</div>
</template>
