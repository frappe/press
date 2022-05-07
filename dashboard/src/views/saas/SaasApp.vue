<template>
	<div class="mt-8 flex-1">
		<div class="text-base text-gray-700">
			<div class="px-4 sm:px-8">
				<Tabs class="pb-8" :tabs="tabs">
					<router-view v-slot="{ Component, route }">
						<component
							v-if="app.data"
							:is="Component"
							:app="app.data"
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
		{ label: 'Overview', route: 'overview' },
		{ label: 'Plans', route: 'plan' }
	];

	let tabsByStatus = {
		Draft: ['Overview', 'Plans'],
		Published: ['Overview', 'Plans']
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
