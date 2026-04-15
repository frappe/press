<script setup lang="ts">
import LucideSearch from '~icons/lucide/search';
import LucideCommand from '~icons/lucide/command';
import { searchModalOpen } from '@/data/ui';
</script>

<template>
	<button
		class="flex items-center rounded px-2.5 py-1.5 md:px-3 md:py-2 text-ink-gray-6 transition gap-2 text-sm w-full mt-1 hover:bg-surface-gray-3"
		@click="() => (searchModalOpen = true)"
	>
		<LucideSearch class="size-4 text-ink-gray-6" />
		<span class="text-left mr-auto"> Search</span>

		<LucideCommand class="size-3.5 text-ink-gray-6" />
		<span class="text-xs">K</span>
	</button>
</template>
