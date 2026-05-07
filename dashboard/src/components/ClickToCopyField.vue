<script setup lang="ts">
import CopyBtn from '@/components/utils/CopyBtn.vue';

interface Props {
	textContent: string;
}

const props = defineProps<Props>();
</script>

<template>
	<div class="flex items-center justify-between rounded bg-surface-gray-2 p-3">
		<pre class="truncate text-xs">{{ textContent }}</pre>
		<CopyBtn :text="textContent" class="ml-2 shrink-0 text-ink-gray-6" />
	</div>
</template>
