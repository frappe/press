<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { isMobile } from '@/utils/device'

defineOptions({ name: 'SiteInsights' })

const tabs = [
	{
		label: 'Analytics',
		value: 'Site Analytics',
	},
	{
		label: 'Reports',
		value: 'Site Performance Reports',
		children: [
			'Site Performance Slow Queries',
			'Site Performance Process List',
			'Site Performance Request Logs',
			'Site Performance Deadlock Report',
		],
	},
	{
		label: 'Logs',
		value: 'Site Logs',
		children: ['Site Log'],
	},
	{
		label: 'Jobs',
		value: 'Site Jobs',
		children: ['Site Job'],
	},
]

const route = useRoute()
const router = useRouter()

onMounted(() => {
	if (route.name === 'Site Insights') {
		router.push({ name: 'Site Analytics' })
	}
})
</script>

<template>
	<div
		class="-m-5 flex divide-x"
		:class="{
			'flex-col': isMobile(),
		}"
	>
		<aside
			class="p-2 gap-1 flex md:flex-col"
			:class="{
				'w-full border-b': isMobile(),
			}"
		>
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value }"
					class="px-2 py-1.5 md:pr-15 flex cursor-pointer text-base text-ink-gray-5 md:rounded hover:bg-surface-gray-1"
					active-class="bg-surface-gray-1 text-ink-gray-9 rounded"
				>
					{{ tab.label }}
				</router-link>
			</template>
		</aside>
		<div class="w-full overflow-auto sm:h-[88vh]">
			<router-view />
		</div>
	</div>
</template>
