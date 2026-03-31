<script setup lang="ts">
import { h, computed, onMounted, onUnmounted, getCurrentInstance } from 'vue';

import DoorOpen from '~icons/lucide/door-open';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
// import Package from '~icons/lucide/package';
import Boxes from '~icons/lucide/boxes';
import Server from '~icons/lucide/server';
import WalletCards from '~icons/lucide/wallet-cards';
import Key from '~icons/lucide/key';
import Settings from '~icons/lucide/settings';
import App from '~icons/lucide/layout-grid';
import DatabaseZap from '~icons/lucide/database-zap';
import Activity from '~icons/lucide/activity';
import Logs from '~icons/lucide/scroll-text';
import Globe from '~icons/lucide/globe';
import Notification from '~icons/lucide/inbox';
import Code from '~icons/lucide/code';
import FileSearch from '~icons/lucide/file-search';
import { unreadNotificationsCount } from '@/data/notifications';

import { getTeam } from '@/data/team';
import { session } from '@/data/session';
import { useRoute } from 'vue-router';

const $route = useRoute();
const $team = getTeam();
const $session = session;
const $socket = getCurrentInstance().proxy.$socket;

const navigation = computed(() => {
	if (!$team?.doc) return [];

	const routeName = String($route?.name || '');
	const onboardingComplete = $team.doc.onboarding.complete;
	const isSaasUser = $team.doc.is_saas_user;
	const enforce2FA = Boolean(
		!$team.doc.is_desk_user &&
			$team.doc.enforce_2fa &&
			!$team.doc.user_info?.is_2fa_enabled,
	);

	return [
		{
			name: 'Welcome',
			icon: DoorOpen,
			route: '/welcome',
			isActive: routeName === 'Welcome',
			condition: !onboardingComplete,
		},
		{
			name: 'Notifications',
			icon: Notification,
			route: '/notifications',
			spacer: true,
			isActive: routeName === 'Press Notification List',
			condition: onboardingComplete && !isSaasUser,
			badge: () => {
				if (unreadNotificationsCount.data > 0) {
					return h(
						'span',
						{
							class: '!ml-auto px-1.5 py-0.5 text-xs text-gray-600',
						},
						unreadNotificationsCount.data > 99
							? '99+'
							: unreadNotificationsCount.data,
					);
				}
			},
			disabled: enforce2FA,
		},
		{
			name: 'Sites',
			icon: PanelTopInactive,
			route: '/sites',
			isActive:
				['Site List', 'Site Detail', 'New Site'].includes(routeName) ||
				routeName.startsWith('Site Detail'),
			disabled: enforce2FA,
		},
		/* {
			name: 'Benches',
			icon: (Package),
			route: '/benches',
			isActive: routeName.startsWith('Bench'),
			condition: $team.doc?.is_desk_user,
			disabled: !onboardingComplete || enforce2FA,
		}, */
		{
			name: 'Benches',
			icon: Boxes,
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
			icon: Server,
			spacer: true,
			route: onboardingComplete ? '/servers' : '/enable-servers',
			isActive:
				['New Server'].includes(routeName) ||
				routeName.startsWith('Server') ||
				routeName === 'Enable Servers',
			disabled: enforce2FA,
		},
		{
			name: 'Dev Tools',
			icon: Code,
			route: '/devtools',
			condition: onboardingComplete && !isSaasUser,
			disabled: enforce2FA,
			children: [
				{
					name: 'Log Browser',
					icon: Logs,
					route: '/log-browser',
					isActive: routeName === 'Log Browser',
				},
				{
					name: 'DB Analyzer',
					icon: Activity,
					route: '/database-analyzer',
					isActive: routeName === 'DB Analyzer',
				},
				{
					name: 'SQL Playground',
					icon: DatabaseZap,
					route: '/sql-playground',
					isActive: routeName === 'SQL Playground',
				},
				{
					name: 'Binlog Browser',
					icon: FileSearch,
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
			icon: App,
			route: '/apps',
			isActive: routeName.startsWith('Marketplace'),
			condition:
				$team.doc?.is_desk_user ||
				(!!$team.doc.is_developer && $session.hasAppsAccess),
			disabled: enforce2FA,
		},
		{
			name: 'Billing',
			icon: WalletCards,
			route: '/billing',
			isActive: routeName.startsWith('Billing'),
			condition: $team.doc?.is_desk_user || $session.hasBillingAccess,
			disabled: enforce2FA,
		},
		{
			name: 'Access Requests',
			icon: Key,
			route: '/access-requests',
			isActive: routeName === 'Access Requests',
			disabled: enforce2FA,
		},
		{
			name: 'Partnership',
			icon: Globe,
			route: '/partners',
			isActive: routeName === 'Partnership',
			condition: Boolean($team.doc.erpnext_partner),
			disabled: enforce2FA,
		},
		{
			name: 'Settings',
			icon: Settings,
			route: '/settings',
			isActive: routeName.startsWith('Settings'),
			disabled: enforce2FA,
		},
		{
			name: 'Status',
			icon: () => h(Globe),
			route: '/status',
			isActive: routeName === 'Status',
			disabled: enforce2FA,
		},
	].filter((item) => item.condition ?? true);
});

onMounted(() => {
	$socket.emit('doctype_subscribe', 'Press Notification');
	$socket.on('press_notification', (data) => {
		if (data.team === $team.doc.name) {
			unreadNotificationsCount.setData((data) => data + 1);
		}
	});
});

onUnmounted(() => {
	$socket.off('press_notification');
});
</script>

<template>
	<slot :navigation="navigation" />
</template>
