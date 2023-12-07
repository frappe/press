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
								class="mt-1 hidden text-sm leading-none text-gray-700 sm:inline"
							>
								{{ $team.get.loading ? 'Loading...' : $team.doc.user }}
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
		<Dialog :options="{ title: 'Change Team' }" v-model="showTeamSwitcher">
			<template #body-content>
				<div class="rounded bg-gray-100 px-2 py-3">
					<div class="text-base text-gray-900">
						Viewing Dashboard as
						<span class="font-medium">{{ $team.doc.user }}</span>
						<span
							class="font-mono text-sm text-gray-500"
							v-if="$team.name != $team.doc.user"
						>
							({{ $team.name }})
						</span>
					</div>
				</div>
				<div class="-mb-3 mt-3 divide-y">
					<div
						class="flex items-center justify-between py-3"
						v-for="team in $team.doc.valid_teams"
						:key="team.name"
					>
						<div>
							<span class="text-base text-gray-800">
								{{ team.user }}
							</span>
							<span
								class="font-mono text-sm text-gray-500"
								v-if="team.name != team.user"
							>
								({{ team.name }})
							</span>
						</div>
						<Badge
							v-if="$team.name === team.name"
							label="Currently Active"
							theme="green"
						/>
						<Button v-else @click="switchToTeam(team.name)">Change</Button>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, h, ref } from 'vue';
import Home from '~icons/lucide/home';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
import Package from '~icons/lucide/package';
import Server from '~icons/lucide/server';
import LayoutPanelTop from '~icons/lucide/layout-panel-top';
import LayoutGrid from '~icons/lucide/layout-grid';
import SquareDashedBottomCode from '~icons/lucide/square-dashed-bottom-code';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';
import { switchToTeam } from '../data/team';
import { useRoute } from 'vue-router';

const $route = useRoute();

const navigation = computed(() => [
	{
		name: 'Shared',
		items: [
			{
				name: 'Sites',
				icon: () => h(PanelTopInactive),
				route: '/sites',
				isActive:
					['Site List', 'Site Detail'].includes($route.name) ||
					$route.name.startsWith('Site Detail')
			},
			{
				name: 'Benches',
				icon: () => h(Package),
				route: '/benches',
				isActive:
					['Release Group List', 'Release Group Detail'].includes(
						$route.name
					) || $route.name.startsWith('Release Group Detail')
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
]);

let showTeamSwitcher = ref(false);
</script>
