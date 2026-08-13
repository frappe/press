<script setup lang="ts">
import { isMobile } from '@/utils/device'

defineOptions({ name: 'SiteBackups' })

const tabs = [
	{
		label: 'Backups',
		value: 'Site Backup List',
	},
	{
		label: 'Audit Trail',
		value: 'Site Backup Audit Trail',
	},
]
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
			<template v-for="tab in tabs" :key="tab.value">
				<router-link
					:to="{ name: tab.value }"
					class="px-2 py-1.5 md:pr-15 flex cursor-pointer whitespace-nowrap text-base text-ink-gray-5 md:rounded hover:bg-surface-gray-1"
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
