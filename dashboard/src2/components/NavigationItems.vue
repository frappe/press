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
import Server from '~icons/lucide/server';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';
import App from '~icons/lucide/layout-grid';
import Globe from '~icons/lucide/globe';
import Notification from '~icons/lucide/inbox';
import { unreadNotificationsCount } from '../data/notifications';

export default {
	name: 'NavigationItems',
	computed: {
		navigation() {
			if (!this.$team?.doc) return [];
			let routeName = this.$route?.name || '';
			let disabled = !this.$team.doc.onboarding.complete;
			return [
				{
					name: 'Welcome',
					icon: () => h(DoorOpen),
					route: '/welcome',
					isActive: routeName === 'Welcome',
					condition: !this.$team.doc.onboarding.complete
				},
				{
					name: 'Notifications',
					icon: () => h(Notification),
					route: '/notifications',
					isActive: routeName === 'Press Notification List',
					condition: this.$team.doc.onboarding.complete,
					badge: () => {
						if (unreadNotificationsCount.data > 0) {
							return h(
								'span',
								{
									class:
										'!ml-auto rounded bg-gray-400 px-1.5 py-0.5 text-xs text-white'
								},
								unreadNotificationsCount.data > 99
									? '99+'
									: unreadNotificationsCount.data
							);
						}
					},
					disabled
				},
				{
					name: 'Sites',
					icon: () => h(PanelTopInactive),
					route: '/sites',
					isActive:
						['Site List', 'Site Detail', 'New Site'].includes(routeName) ||
						routeName.startsWith('Site Detail')
				},
				{
					name: 'Benches',
					icon: () => h(Package),
					route: '/benches',
					isActive:
						[
							'Release Group List',
							'Release Group Detail',
							'New Release Group',
							'Bench New Site',
							'Bench Deploy'
						].includes(routeName) ||
						routeName.startsWith('Release Group Detail'),
					disabled
				},
				{
					name: 'Servers',
					icon: () => h(Server),
					route: '/servers',
					isActive:
						['New Server'].includes(routeName) ||
						routeName.startsWith('Server'),
					disabled
				},
				{
					name: 'Apps',
					icon: () => h(App),
					route: '/apps',
					isActive: routeName.startsWith('Marketplace'),
					disabled
				},
				{
					name: 'Billing',
					icon: () => h(WalletCards),
					route: '/billing',
					isActive: routeName.startsWith('Billing'),
					disabled
				},
				{
					name: 'Partners',
					icon: () => h(Globe),
					route: '/partners',
					isActive: routeName.startsWith('Partners'),
					condition: Boolean(this.$team.doc.erpnext_partner),
					disabled
				},
				{
					name: 'Settings',
					icon: () => h(Settings),
					route: '/settings',
					isActive: routeName.startsWith('Settings'),
					disabled
				}
			].filter(item => item.condition !== false);
		}
	},
	mounted() {
		this.$socket.emit('doctype_subscribe', 'Press Notification');
		this.$socket.on('press_notification', data => {
			if (data.team === this.$team.doc.name) {
				unreadNotificationsCount.setData(data => data + 1);
			}
		});
	},
	unmounted() {
		this.$socket.off('press_notification');
	}
};
</script>
