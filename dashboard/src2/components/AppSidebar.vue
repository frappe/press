<template>
	<div class="min-h-screen w-[220px] border-r bg-gray-50">
		<div class="p-2">
			<Dropdown
				:options="[
					{
						label: 'Change Team',
						icon: 'command',
						onClick: () => (showTeamSwitcher = true)
					},
					{
						label: 'Support & Docs',
						icon: 'help-circle',
						onClick: support
					},
					{
						label: 'Logout',
						icon: 'log-out',
						onClick: $session.logout.submit
					}
				]"
			>
				<template v-slot="{ open }">
					<button
						class="flex w-[204px] items-center rounded-md px-2 py-2 text-left"
						:class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
					>
						<FCLogo class="h-8 w-8 shrink-0 rounded" />
						<div class="ml-2 flex flex-1 flex-col overflow-hidden">
							<div class="text-base font-medium leading-none text-gray-900">
								Frappe Cloud
							</div>
							<Tooltip :text="$team?.doc?.user || null">
								<div
									class="mt-1 hidden overflow-hidden text-ellipsis whitespace-nowrap text-sm leading-none text-gray-700 sm:inline"
								>
									{{ $team?.get.loading ? 'Loading...' : $team.doc.user }}
								</div>
							</Tooltip>
						</div>
						<FeatherIcon
							name="chevron-down"
							class="ml-auto h-5 w-5 text-gray-700"
						/>
					</button>
				</template>
			</Dropdown>
		</div>
		<nav class="px-2">
			<template v-for="(item, i) in navigation">
				<template v-if="item.items">
					<div
						class="py-1 text-sm leading-5 text-gray-600"
						:class="{ 'mt-2': i != 0 }"
					>
						{{ item.name }}
					</div>
					<div class="space-y-0.5">
						<AppSidebarItem
							v-for="subItem in item.items"
							:key="subItem.name"
							:item="subItem"
						/>
					</div>
				</template>
				<AppSidebarItem class="mt-0.5" v-else :key="item.name" :item="item" />
			</template>
		</nav>
		<!-- TODO: update component name after dashboard-beta merges -->
		<SwitchTeamDialog2 v-model="showTeamSwitcher" />
	</div>
</template>

<script>
import { h, defineAsyncComponent } from 'vue';
import AppSidebarItem from './AppSidebarItem.vue';
import DoorOpen from '~icons/lucide/door-open';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
import Package from '~icons/lucide/package';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';
import Globe from '~icons/lucide/globe';
import { Tooltip } from 'frappe-ui';

export default {
	name: 'AppSidebar',
	components: {
		AppSidebarItem,
		SwitchTeamDialog2: defineAsyncComponent(() =>
			import('./SwitchTeamDialog.vue')
		),
		Tooltip
	},
	data() {
		return {
			showTeamSwitcher: false
		};
	},
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
						['Site List', 'Site Detail', 'NewSite'].includes(routeName) ||
						routeName.startsWith('Site Detail'),
					disabled
				},
				{
					name: 'Benches',
					icon: () => h(Package),
					route: '/benches',
					isActive:
						[
							'Release Group List',
							'Release Group Detail',
							'NewBench',
							'NewBenchSite'
						].includes(routeName) ||
						routeName.startsWith('Release Group Detail'),
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
					condition: this.$team.doc.erpnext_partner,
					disabled
				}
			].filter(item => item.condition !== false);
		}
	},
	methods: {
		support() {
			window.open('https://frappecloud.com/support', '_blank');
		}
	}
};
</script>
