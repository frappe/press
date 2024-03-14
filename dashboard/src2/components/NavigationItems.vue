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
import Globe from '~icons/lucide/globe';

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
					name: 'Billing',
					icon: () => h(WalletCards),
					route: '/billing',
					isActive: routeName.startsWith('Billing'),
					disabled
				},
				{
					name: 'Settings',
					icon: () => h(Settings),
					route: '/settings',
					isActive: routeName.startsWith('Settings'),
					disabled
				},
				{
					name: 'Partners',
					icon: () => h(Globe),
					route: '/partners',
					isActive: routeName.startsWith('Partners'),
					condition: Boolean(this.$team.doc.erpnext_partner),
					disabled
				}
				// {
				// 	name: 'Notifications',
				// 	icon: () => h(Notification),
				// 	route: '/notifications',
				// 	isActive: routeName.startsWith('Notification'),
				// 	disabled
				// }
			].filter(item => item.condition !== false);
		}
	}
};
</script>
