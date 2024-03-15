<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
	</Header>
	<div>
		<TabsWithRouter :tabs="tabs">
			<template #tab-content="{ tab }">
				<router-view :key="tab.routeName"></router-view>
			</template>
		</TabsWithRouter>
	</div>
</template>

<script setup>
import Header from '../components/Header.vue';
import { Breadcrumbs } from 'frappe-ui';
import { provide, ref } from 'vue';
import { icon } from '../utils/components';
import TabsWithRouter from '../components/TabsWithRouter.vue';

const tabs = [
	{
		label: 'Profile',
		icon: icon('user'),
		routeName: 'SettingsProfile'
	},
	{
		label: 'Team',
		icon: icon('users'),
		routeName: 'SettingsTeam'
	},
	{
		label: 'Developer',
		icon: icon('code'),
		routeName: 'SettingsDeveloper'
	},
	{
		label: 'Permissions',
		icon: icon('lock'),
		routeName: 'SettingsPermission',
		childrenRoutes: [
			'SettingsPermissionGroupList',
			'SettingsPermissionGroupPermissions'
		]
	}
];

const breadcrumbs = ref([{ label: 'Settings', route: '/settings' }]);
provide('breadcrumbs', breadcrumbs);
</script>
