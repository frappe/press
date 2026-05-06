<script setup lang="ts">
import LucideSearch from '~icons/lucide/search';
import { searchModalOpen } from '@/data/ui';
import { isMac } from '@/utils/device';
</script>

<template>
	<button
		class="flex items-center rounded px-2 py-1.5 text-ink-gray-6 transition gap-2 text-sm w-full hover:bg-surface-gray-2"
		@click="() => (searchModalOpen = true)"
	>
		<LucideSearch class="size-4 text-ink-gray-6" />
		<span class="text-left mr-auto">Search</span>
		<span v-if="isMac()" class="inline-flex items-center text-sm">
			<!-- using a container to align ⌘ and K and setting font-medium to optically correct the alignment -->
			<span class="text-sm font-medium">⌘</span>
			<span class="text-sm">K</span>
		</span>
		<span v-else class="inline-flex items-center text-sm">Ctrl+K</span>
	</button>
</template>
