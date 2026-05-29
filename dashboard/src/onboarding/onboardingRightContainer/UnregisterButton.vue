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
		return 'This will remove your partner registration and revoke partner privileges on your account.'
	}
	return 'If you unregister your company from the partnership, all associated data will be deleted. You can reapply for partnership in the future, but your company will need to go through the eligibility review process again.'
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
		open.value = false
		showOnboardingToast('success', 'Partner registration removed')
		await team?.reload?.()
		// reroute the user back to create site page
		router.push({ path: '/sites' })
	} catch (error: any) {
		showOnboardingToast(
			'error',
			error.messages?.[0] || error.message || 'Could not unregister',
		)
	}
}
</script>

<template>
	<Dialog v-model="open" :options="dialogOptions">
		<template #body-content>
			<p class="text-p-base text-ink-gray-8">
				{{ confirmMessage }}
			</p>
		</template>
	</Dialog>
</template>
