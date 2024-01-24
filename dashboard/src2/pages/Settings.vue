<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
	</Header>
	<div>
		<Tabs
			v-model="currentTab"
			:tabs="tabs"
			@update:model-value="handleTabChange($event)"
		>
			<template #default="{ tab }">
				<router-view :key="tab.routeName"></router-view>
			</template>
		</Tabs>
	</div>
</template>

<script setup>
import Header from '../components/Header.vue';
import { Breadcrumbs, Tabs } from 'frappe-ui';
import { onMounted, provide, ref, watch } from 'vue';
import { onBeforeRouteUpdate, useRouter } from 'vue-router';
import { icon } from '../utils/components';

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
		label: 'Permissions',
		icon: icon('lock'),
		routeName: 'SettingsPermission'
	}
];

const currentTab = ref(0);
const router = useRouter();

const breadcrumbs = ref([{ label: 'Settings', route: '/settings' }]);
provide('breadcrumbs', breadcrumbs);

onBeforeRouteUpdate((to, from, next) => {
	setTabToRoute(to);
	next();
});
onMounted(() => {
	const route = router.currentRoute.value;
	setTabToRoute(route);
});
function setTabToRoute(route) {
	tabs.some((tab, index) => {
		if (
			tab.routeName === route.name ||
			route.matched.some(record => record.name === tab.routeName)
		) {
			currentTab.value = index;
			return true;
		}
	});
}
function handleTabChange(tabIndex) {
	router.replace({ name: tabs[tabIndex].routeName });
}
</script>
