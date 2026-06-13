<script setup lang="ts">
import { Dialog } from 'frappe-ui'
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { showOnboardingToast } from '@/onboarding/toast'
import { usePartnerOnboarding } from '@/onboarding/usePartnerOnboarding'

type TeamResource = {
	reload?: () => Promise<void>
}

const team = inject<TeamResource>('team')
const onboarding = usePartnerOnboarding(team as any)
const open = defineModel<boolean>({ default: false })
const router = useRouter()
const unregistering = onboarding.unregistering

const confirmMessage = computed(() => {
	if (onboarding.doc.value?.status === 'Approved') {
		return 'This removes your partner registration and partner privileges.'
	}
	return 'This deletes your current application. You can reapply later, but the company will need to go through review again.'
})

const dialogOptions = computed(() => ({
	title: 'Unregister partnership?',
	actions: [
		{
			label: 'Unregister',
			theme: 'red',
			variant: 'solid' as const,
			loading: unregistering.value,
			onClick: unregister,
		},
	],
}))

async function unregister() {
	if (unregistering.value) return

	try {
		await onboarding.unregister()
	} catch (error: any) {
		showOnboardingToast(
			'error',
			error.messages?.[0] || error.message || 'Could not unregister',
		)
		return
	}

	// onboarding.unregister() already reloads the team (see usePartnerOnboarding),
	// so leave the onboarding page right away — don't gate routing on a reload.
	open.value = false
	showOnboardingToast('success', 'Partner registration removed')
	router.push({ name: 'Site List' })
}
</script>

<template>
	<Dialog v-model="open" v-bind="dialogOptions">
		<p class="-mt-2 -mb-3 text-p-base leading-6 text-ink-gray-8">
			{{ confirmMessage }}
		</p>
	</Dialog>
</template>
