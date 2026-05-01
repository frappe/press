<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';

interface Props {
	textContent: string;
	breakLines?: boolean;
	class?: string;
}

const props = defineProps<Props>();
const copied = ref(false);

const copyTextContentToClipboard = () => {
	const clipboard = window.navigator.clipboard;
	clipboard.writeText(props.textContent).then(() => {
		copied.value = true;
		setTimeout(() => {
			copied.value = false;
		}, 4000);
		toast.success('Copied to clipboard!');
	});
};
</script>

<template>
	<div class="flex items-center justify-between rounded bg-surface-gray-2 p-3">
		<pre class="truncate text-xs">{{ textContent }}</pre>
		<button
			class="ml-2 shrink-0 rounded-sm text-xs text-ink-gray-6 hover:text-ink-gray-9"
			@click="copyTextContentToClipboard"
		>
    <lucide-clipboard v-if='!copied' class='size-3.5'/>
    <lucide-clipboard-check v-else class='size-3.5'/>
		</button>
	</div>
</template>
