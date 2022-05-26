<template>
	<div class="mt-8 flex-1">
		<div class="text-base text-gray-700">
			<div class="px-4 sm:px-8">
				<div class="text-base text-gray-700">
					<router-link to="/saas/manage" class="hover:text-gray-800">
						← Back to Apps
					</router-link>
				</div>

				<div
					v-if="app.data"
					class="my-4 flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ app.data.title }}</h1>
						<Badge
							class="ml-4 hidden md:inline-block"
							:status="app.data.status"
							>{{ app.data.status }}</Badge
						>
					</div>
				</div>

				<Tabs class="pb-8" :tabs="tabs">
					<router-view v-slot="{ Component, route }">
						<component
							v-if="app.data"
							:is="Component"
							:app="app.data"
							:appName="props.appName"
						></component>
					</router-view>
				</Tabs>
			</div>
		</div>
	</div>
</template>

<script setup>
import Tabs from '@/components/Tabs.vue';
import { computed } from 'vue';
import useResource from '@/composables/resource';

const props = defineProps({ appName: String });

const app = useResource({
	method: 'press.api.saas.get_app',
	auto: true,
	params: {
		name: props.appName
	}
});

const tabs = computed(() => {
	let tabRoute = subRoute => `/saas/manage/${props.appName}/${subRoute}`;
	let tabs = [
		{ label: 'Plans', route: 'plan' },
		{ label: 'Benches', route: 'benches' },
		{ label: 'Settings', route: 'settings' }
	];

	let tabsByStatus = {
		Draft: ['Plans', 'Benches', 'Settings'],
		Published: ['Plans', 'Benches', 'Settings']
	};
	if (props.appName) {
		let tabsToShow = tabsByStatus['Draft'];
		if (tabsToShow?.length) {
			tabs = tabs.filter(tab => tabsToShow.includes(tab.label));
		}
		return tabs.map(tab => {
			return {
				...tab,
				route: tabRoute(tab.route)
			};
		});
	}
	return [];
});
</script>
