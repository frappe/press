<template>
	<div class="mt-8 flex-1">
		<div class="text-base text-gray-700">
			<div class="px-4 sm:px-8">
				<Tabs class="pb-8" :tabs="tabs">
					<router-view v-slot="{ Component, route }">
						<component
							v-if="subData"
							:is="Component"
							:subName="props.subName"
							:subData="subData"
							:site="subData.site"
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

const props = defineProps({ subName: String });

const subscription = useResource({
	method: 'press.api.saas.subscription_overview',
	params: {
		name: props.subName
	},
	auto: true
});

const subData = computed(() => {
	return subscription.data;
});

const tabs = computed(() => {
	let tabRoute = subRoute => `/saas/subscription/${props.subName}/${subRoute}`;
	let tabs = [
		{ label: 'Overview', route: 'overview' },
		{ label: 'Plans', route: 'plan' },
		{ label: 'Backups', route: 'database' },
		{ label: 'Jobs', route: 'jobs' }
	];

	let tabsByStatus = {
		Draft: ['Overview', 'Plans', 'Backups', 'Jobs'],
		Published: ['Overview', 'Plans', 'Backups', 'Jobs']
	};
	if (props.subName) {
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
