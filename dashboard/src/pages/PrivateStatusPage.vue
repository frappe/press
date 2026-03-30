<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs :items="[{ label: 'Status', route: '/status' }]" />
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
import TabsWithRouter from '../components/TabsWithRouter.vue';

const tabs = [
	{
		label: 'Ongoing Incidents',
		icon: LucideTriangleAlert,
		routeName: 'OngoingIncidents',
	},
	{
		label: 'Incident History',
		icon: LucideArchive,
		routeName: 'IncidentHistory',
	},
];
</script>
