<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs :items="[{ label: 'Settings', route: '/settings' }]" />
		</div>
	</Header>
	<div>
		<TabsWithRouter :tabs="tabs">
			<template #tab-item="{ tab }">
				<router-link
					:to="{ name: tab.routeName }"
					class="flex whitespace-nowrap items-center py-2.5 gap-1.5 text-base text-ink-gray-5 duration-300 ease-in-out hover:text-ink-gray-9 data-[state=active]:text-ink-gray-9"
				>
					<component v-if="tab.icon" :is="tab.icon" class="size-4"> </component>

					{{ tab.label }}
				</router-link>
			</template>
			<template #tab-content="{ tab }">
				<router-view :key="tab.routeName"></router-view>
			</template>
		</TabsWithRouter>
	</div>
</template>

<script setup>
import Header from '../components/Header.vue';
import { Breadcrumbs } from 'frappe-ui';
import { icon } from '../utils/components';
import TabsWithRouter from '../components/TabsWithRouter.vue';
import { getTeam } from '../data/team';
import { session } from '../data/session';

let $team = getTeam();
let $session = session || {};

const tabs = [
	{
		label: 'Profile',
		icon: icon('user'),
		routeName: 'SettingsProfile',
	},
	{
		label: 'Team',
		icon: icon('users'),
		routeName: 'SettingsTeam',
		condition: () =>
			$team.doc?.user === $session.user ||
			$session.isTeamAdmin ||
			$session.isSystemUser,
	},
	{
		label: 'Roles',
		icon: icon('lock'),
		routeName: 'SettingsPermission',
		childrenRoutes: [
			'SettingsPermissionRoles',
			'SettingsPermissionRolePermissions',
		],
		condition: () =>
			$team.doc?.user === $session.user ||
			$session.isTeamAdmin ||
			$session.isSystemUser,
	},
	{
		label: 'Developer',
		icon: icon('code'),
		routeName: 'SettingsDeveloper',
	},
];
</script>
