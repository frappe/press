<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { unreadNotificationsCount } from '@/data/notifications'
import { session } from '@/data/session'
import { getTeam } from '@/data/team'
import { searchModalOpen } from '@/data/ui'
import { isMac } from '@/utils/device'
import NotificationPanel from './Notifications.vue'
import { useRealtimeNotifs } from './useRealtimeNotifs'

const $route = useRoute()
const $team = getTeam()
const $session = session

const list = computed(() => {
	if (!$team?.doc) return []

	const routeName = String($route?.name || '')
	const onboardingComplete = $team.doc.onboarding.complete
	const activePartner = Boolean(
		$team.doc.erpnext_partner && $team.doc.partner_status === 'Active',
	)
	const isSaasUser = $team.doc.is_saas_user

	const enforce2FA = Boolean(
		!$team.doc.is_desk_user &&
			$team.doc.enforce_2fa &&
			!$team.doc.user_info?.is_2fa_enabled,
	)

	return [
		{
			name: 'Welcome',
			icon: LucideDoorOpen,
			route: '/welcome',
			isActive: routeName === 'Welcome',
			condition: !onboardingComplete,
		},

		{
			icon: LucideSearch,
			name: 'Search',
			is: 'BUTTON',
			condition: onboardingComplete,
			suffix: isMac() ? '⌘ K' : 'Ctrl+k',
			onClick: () => (searchModalOpen.value = true),
		},

		{
			name: 'Notifications',
			condition: onboardingComplete && !isSaasUser,
			customComponent: NotificationPanel,
			disabled: enforce2FA,
		},

		{
			name: 'Sites',
			icon: LucidePanelTopInactive,
			route: '/sites',
			class: 'mt-1.5',
			isActive:
				['Site List', 'Site Detail', 'New Site'].includes(routeName) ||
				routeName.startsWith('Site Detail'),
			disabled: enforce2FA,
		},

		{
			name: 'Benches',
			icon: LucideBoxes,
			route: onboardingComplete ? '/groups' : '/enable-bench-groups',
			isActive:
				[
					'Release Group List',
					'Release Group Detail',
					'New Release Group',
					'Release Group New Site',
					'Deploy Candidate',
				].includes(routeName) ||
				routeName.startsWith('Release Group Detail') ||
				routeName === 'Enable Benches',
			disabled: enforce2FA,
		},

		{
			name: 'Servers',
			icon: LucideServer,
			route: onboardingComplete ? '/servers' : '/enable-servers',
			isActive:
				['New Server'].includes(routeName) ||
				routeName.startsWith('Server') ||
				routeName === 'Enable Servers',
			disabled: enforce2FA,
		},

		{
			name: 'Dev Tools',
			icon: LucideCode,
			route: '/devtools',
			condition: onboardingComplete && !isSaasUser,
			disabled: enforce2FA,
			children: [
				{
					name: 'Log Browser',
					icon: LucideScrollText,
					route: '/log-browser',
					isActive: routeName === 'Log Browser',
				},
				{
					name: 'DB Analyzer',
					icon: LucideActivity,
					route: '/database-analyzer',
					isActive: routeName === 'DB Analyzer',
				},
				{
					name: 'SQL Playground',
					icon: LucideDatabaseZap,
					route: '/sql-playground',
					isActive: routeName === 'SQL Playground',
				},
				{
					name: 'Binlog Browser',
					icon: LucideFileSearch,
					route: '/binlog-browser',
					isActive: routeName === 'Binlog Browser',
					condition: $team.doc.is_binlog_indexer_enabled ?? false,
				},
			].filter((item) => item.condition ?? true),

			isActive: [
				'SQL Playground',
				'DB Analyzer',
				'Log Browser',
				'Binlog Browser',
			].includes(routeName),
		},

		{
			name: 'Marketplace',
			icon: LucideLayoutGrid,
			route: '/apps',
			isActive: routeName.startsWith('Marketplace'),
			css: '-mt-1',
			condition:
				$team.doc?.is_desk_user ||
				(!!$team.doc.is_developer && $session.hasAppsAccess),
			disabled: enforce2FA,
		},

		{
			name: 'Billing',
			icon: LucideWalletCards,
			route: '/billing',
			isActive: routeName.startsWith('Billing'),
			condition: $team.doc?.is_desk_user || $session.hasBillingAccess,
			disabled: enforce2FA,
		},

		{
			name: 'Partnership',
			icon: LucideGlobe,
			route: activePartner ? '/partners' : '/partner-onboarding',
			isActive:
				$route.path.startsWith('/partners') ||
				routeName === 'Partner Onboarding',
			disabled: enforce2FA,
		},

		{
			name: 'Settings',
			icon: LucideSettings,
			route: '/settings',
			isActive: routeName.startsWith('Settings'),
			disabled: enforce2FA,
		},

		{
			name: 'Status',
			icon: LucideActivity,
			route: '/status',
			isActive: routeName === 'Status',
			disabled: enforce2FA,
		},
	].filter((item) => item.condition ?? true)
})

useRealtimeNotifs((data) => {
	if (data.team === $team.doc.name) {
		unreadNotificationsCount.setData((data: number) => data + 1)
	}
})
</script>

<template>
	<slot :list />
</template>
