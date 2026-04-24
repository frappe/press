<script setup lang="ts">
import LucideSearch from '~icons/lucide/search';
import { searchModalOpen } from '@/data/ui';
import { isMac } from '@/utils/device';
</script>

<template>
	<button
		class="flex items-center rounded px-2 py-1.5 text-ink-gray-6 transition gap-1 text-sm w-full md:mt-1 hover:bg-surface-gray-2"
		@click="() => (searchModalOpen = true)"
	>
		<LucideSearch class="size-4 text-ink-gray-6 mr-1" />
		<span class="text-left mr-auto">Search</span>
		<span class="text-xs"> {{ isMac() ? '⌘ K' : 'Ctrl+K' }}</span>
	</button>
</template>
