<template>
	<div>
		<slot :navigation="navigation" />
	</div>
</template>
<script>
import { h } from 'vue';
import DoorOpen from '~icons/lucide/door-open';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
import Package from '~icons/lucide/package';
import Boxes from '~icons/lucide/boxes';
import Server from '~icons/lucide/server';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';
import App from '~icons/lucide/layout-grid';
import DatabaseZap from '~icons/lucide/database-zap';
import Activity from '~icons/lucide/activity';
import Logs from '~icons/lucide/scroll-text';
import Globe from '~icons/lucide/globe';
import Shield from '~icons/lucide/shield';
import Notification from '~icons/lucide/inbox';
import Code from '~icons/lucide/code';
import { unreadNotificationsCount } from '../data/notifications';

export default {
	name: 'NavigationItems',
	computed: {
		navigation() {
			if (!this.$team?.doc) return [];

			const routeName = this.$route?.name || '';
			const onboardingComplete = this.$team.doc.onboarding.complete;
			const isSaasUser = this.$team.doc.is_saas_user;
			const enforce2FA = Boolean(
				!this.$team.doc.is_desk_user &&
					this.$team.doc.enforce_2fa &&
					!this.$team.doc.user_info?.is_2fa_enabled,
			);

			return [
				{
					name: 'Welcome',
					icon: () => h(DoorOpen),
					route: '/welcome',
					isActive: routeName === 'Welcome',
					condition: !onboardingComplete,
				},
				{
					name: 'Notifications',
					icon: () => h(Notification),
					route: '/notifications',
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
					icon: () => h(PanelTopInactive),
					route: '/sites',
					isActive:
						['Site List', 'Site Detail', 'New Site'].includes(routeName) ||
						routeName.startsWith('Site Detail'),
					disabled: enforce2FA,
				},
				{
					name: 'Benches',
					icon: () => h(Package),
					route: '/benches',
					isActive: routeName.startsWith('Bench'),
					condition: this.$team.doc?.is_desk_user,
					disabled: !onboardingComplete || enforce2FA,
				},
				{
					name: 'Bench Groups',
					icon: () => h(Boxes),
					route: '/groups',
					isActive:
						[
							'Release Group List',
							'Release Group Detail',
							'New Release Group',
							'Release Group New Site',
							'Deploy Candidate',
						].includes(routeName) ||
						routeName.startsWith('Release Group Detail'),
					condition: onboardingComplete && !isSaasUser,
					disabled: enforce2FA,
				},
				{
					name: 'Servers',
					icon: () => h(Server),
					route: '/servers',
					isActive:
						['New Server'].includes(routeName) ||
						routeName.startsWith('Server'),
					condition: onboardingComplete && !isSaasUser,
					disabled: enforce2FA,
				},
				{
					name: 'Marketplace',
					icon: () => h(App),
					route: '/apps',
					isActive: routeName.startsWith('Marketplace'),
					condition:
						this.$team.doc?.is_desk_user ||
						(!!this.$team.doc.is_developer && this.$session.hasAppsAccess),
					disabled: enforce2FA,
				},
				{
					name: 'Dev Tools',
					icon: () => h(Code),
					route: '/devtools',
					condition: onboardingComplete && !isSaasUser,
					disabled: enforce2FA,
					children: [
						{
							name: 'SQL Playground',
							icon: () => h(DatabaseZap),
							route: '/sql-playground',
							isActive: routeName === 'SQL Playground',
						},
						{
							name: 'Log Browser',
							icon: () => h(Logs),
							route: '/log-browser',
							isActive: routeName === 'Log Browser',
						},
						{
							name: 'DB Analyzer',
							icon: () => h(Activity),
							route: '/database-analyzer',
							isActive: routeName === 'DB Analyzer',
						},
					].filter((item) => item.condition ?? true),
					isActive: ['SQL Playground', 'DB Analyzer', 'Log Browser'].includes(
						routeName,
					),
					disabled: enforce2FA,
				},
				{
					name: 'Billing',
					icon: () => h(WalletCards),
					route: '/billing',
					isActive: routeName.startsWith('Billing'),
					condition:
						this.$team.doc?.is_desk_user || this.$session.hasBillingAccess,
					disabled: enforce2FA,
				},
				{
					name: 'Partnership',
					icon: () => h(Globe),
					route: '/partners',
					isActive: routeName === 'Partnership',
					condition: Boolean(this.$team.doc.erpnext_partner),
					disabled: enforce2FA,
				},
				{
					name: 'Settings',
					icon: () => h(Settings),
					route: '/settings',
					isActive: routeName.startsWith('Settings'),
					disabled: enforce2FA,
				},
				{
					name: 'Partner Admin',
					icon: () => h(Shield),
					route: '/partner-admin',
					isActive: routeName === 'Partner Admin',
					condition: Boolean(this.$team.doc.is_desk_user),
				},
			].filter((item) => item.condition ?? true);
		},
	},
	mounted() {
		this.$socket.emit('doctype_subscribe', 'Press Notification');
		this.$socket.on('press_notification', (data) => {
			if (data.team === this.$team.doc.name) {
				unreadNotificationsCount.setData((data) => data + 1);
			}
		});
	},
	unmounted() {
		this.$socket.off('press_notification');
	},
};
</script>
