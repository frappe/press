<template>
	<div class="mt-8 flex-1" v-if="subData">
		<div class="text-base text-gray-700">
			<div class="px-4 sm:px-8">
				<div class="text-base text-gray-700">
					<router-link to="/saas/subscription" class="hover:text-gray-800">
						← Back to Subscriptions
					</router-link>
				</div>

				<div
					class="my-4 flex flex-col space-y-3 md:flex-row md:items-baseline md:justify-between md:space-y-0"
				>
					<div class="mt-2 flex items-center">
						<h1 class="text-2xl font-bold">{{ subData.site.name }}</h1>
						<Badge
							class="ml-4 hidden md:inline-block"
							:status="subData.site.status"
							>{{ subData.site.status }}</Badge
						>
					</div>
				</div>

				<Tabs class="pb-8" :tabs="tabs">
					<router-view v-slot="{ Component, route }">
						<component
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
	auto: true,
	onSuccess(r) {
		console.log(r);
	}
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
