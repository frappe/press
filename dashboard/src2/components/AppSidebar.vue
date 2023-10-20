<template>
	<div class="min-h-screen w-[220px] border-r bg-gray-50">
		<div class="p-2">
			<Dropdown
				:options="[
					{
						label: 'Switch Team',
						icon: 'command',
						onClick: () => (this.showTeamSwitcher = true)
					},
					{
						label: 'Support & Docs',
						icon: 'help-circle',
						onClick: () => (window.location.href = '/support')
					},
					{
						label: 'Settings',
						icon: 'settings',
						onClick: () => this.$router.push('/settings/profile')
					},
					{
						label: 'Logout',
						icon: 'log-out',
						onClick: () => this.$auth.logout()
					}
				]"
			>
				<template v-slot="{ open }">
					<button
						class="flex w-[204px] items-center rounded-md px-2 py-2 text-left"
						:class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
					>
						<FCLogo class="h-8 w-8 rounded" />
						<div class="ml-2 flex flex-col">
							<div class="text-base font-medium leading-none text-gray-900">
								Frappe Cloud
							</div>
							<div
								v-if="$session.user"
								class="mt-1 hidden text-sm leading-none text-gray-700 sm:inline"
							>
								{{ $session.user }}
							</div>
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
			<template v-for="item in navigation">
				<template v-if="item.items">
					<div class="mt-2 py-1 text-sm leading-5 text-gray-600">
						{{ item.name }}
					</div>
					<div class="space-y-0.5">
						<SidebarItem
							v-for="subItem in item.items"
							:key="subItem.name"
							:item="subItem"
						/>
					</div>
				</template>
				<SidebarItem class="mt-0.5" v-else :key="item.name" :item="item" />
			</template>
		</nav>
	</div>
</template>

<script setup>
import { h } from 'vue';
import Home from '~icons/lucide/home';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
import Package from '~icons/lucide/package';
import Server from '~icons/lucide/server';
import LayoutPanelTop from '~icons/lucide/layout-panel-top';
import LayoutGrid from '~icons/lucide/layout-grid';
import SquareDashedBottomCode from '~icons/lucide/square-dashed-bottom-code';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';

const navigation = [
	{
		name: 'Home',
		icon: () => h(Home),
		route: '/'
	},
	{
		name: 'Shared',
		items: [
			{
				name: 'Sites',
				icon: () => h(PanelTopInactive),
				route: '/sites'
			},
			{
				name: 'Benches',
				icon: () => h(Package),
				route: '/benches'
			}
		]
	},
	{
		name: 'Dedicated',
		items: [
			{
				name: 'Servers',
				icon: () => h(Server),
				route: '/servers'
			},
			{
				name: 'Clusters',
				icon: () => h(LayoutPanelTop),
				route: '/clusters'
			}
		]
	},
	{
		name: 'Hybrid',
		items: [
			{
				name: 'Servers',
				icon: () => h(Server),
				route: '/servers'
			},
			{
				name: 'Clusters',
				icon: () => h(LayoutPanelTop),
				route: '/clusters'
			}
		]
	},
	{
		name: 'Developer',
		items: [
			{
				name: 'Apps',
				icon: () => h(LayoutGrid),
				route: '/apps'
			},
			{
				name: 'Codespaces',
				icon: () => h(SquareDashedBottomCode),
				route: '/codespaces'
			}
		]
	},
	{
		name: 'Account',
		items: [
			{
				name: 'Billing',
				icon: () => h(WalletCards),
				route: '/billing'
			},
			{
				name: 'Settings',
				icon: () => h(Settings),
				route: '/settings'
			}
		]
	}
];
</script>
