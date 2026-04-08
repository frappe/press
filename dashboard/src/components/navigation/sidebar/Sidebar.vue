<script setup lang="ts">
import { Tooltip } from 'frappe-ui';
import LucideChevronDown from '~icons/lucide/chevron-down';
import { ref, defineAsyncComponent } from 'vue';

import Item from './Item.vue';
import NavList from './NavList.vue';
import ItemGroup from './ItemGroup.vue';

import { getTeam } from '@/data/team';
import { session } from '@/data/session';

const $team = getTeam();
const $session = session;

const showTeamSwitcher = ref(false);

const SwitchTeamDialog2 = defineAsyncComponent(
	() => import('../../SwitchTeamDialog.vue'),
);

const docs = () => {
	window.open('https://docs.frappe.io/cloud', '_blank');
};

const feedback = () => {
	window.open('https://frappecloud.com/frappe-cloud-feedback/new', '_blank');
};
</script>

<template>
	<div
		class="relative flex min-h-screen w-[220px] flex-col border-r bg-gray-50"
	>
		<div class="p-2">
			<Dropdown
				:options="[
					{
						label: 'Change Team',
						icon: 'command',
						condition: () =>
							$team?.doc?.valid_teams?.length > 1 || $team?.doc?.is_desk_user,
						onClick: () => (showTeamSwitcher = true),
					},
					{
						label: 'Support & Docs',
						icon: 'help-circle',
						onClick: docs,
					},
					{
						label: 'Share Feedback',
						icon: 'file-text',
						onClick: feedback,
					},
					{
						label: 'Logout',
						icon: 'log-out',
						onClick: $session.logout.submit,
					},
				]"
			>
				<template v-slot="{ open }">
					<button
						class="flex w-[204px] items-center rounded-md px-2 py-2 text-left"
						:class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
					>
						<FCLogo class="mb-1 h-8 w-8 shrink-0 rounded" />
						<div class="ml-2 flex flex-1 flex-col overflow-hidden">
							<div class="text-base font-medium leading-none text-gray-900">
								Frappe Cloud
							</div>
							<Tooltip :text="$team?.doc?.user || null">
								<div
									class="mt-1 hidden overflow-hidden text-ellipsis whitespace-nowrap pb-1 text-sm leading-none text-gray-700 sm:inline"
								>
									{{ $team?.get.loading ? 'Loading...' : $team?.doc?.user }}
								</div>
							</Tooltip>
						</div>
						<LucideChevronDown class="ml-auto size-4" />
					</button>
				</template>
			</Dropdown>
		</div>

		<nav class="px-2">
			<NavList>
				<template v-slot="{ navigation }">
					<template v-for="(item, _) in navigation" :key="item.name">
						<ItemGroup v-if="item.children" :item="item" />
						<component
							v-else-if="item.customComponent"
							:is="item.customComponent"
							:item="item"
						/>
						<Item class="mt-0.5" v-else :item="item" />
					</template>
				</template>
			</NavList>
		</nav>
		<!-- TODO: update component name after dashboard-beta merges -->
		<SwitchTeamDialog2
			v-model="showTeamSwitcher"
			:key="String(showTeamSwitcher)"
		/>
	</div>
</template>
