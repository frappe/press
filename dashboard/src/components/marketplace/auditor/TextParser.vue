<!-- This component is used to parse text provided to render relevant components

- for hyperlinks, wrap the url in <a> tags and make it a component
- for code blocks, wrap the code in <code> tags and make it a component


- For now this is all that it does, we can extend this depending on the use case later.
-->
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
	text: string
}>()

/**
 * Splits text into segments of plain text, URLs, and backtick-wrapped code.
 * Order: URLs are matched first, then inline `code` in the remaining text.
 */
const segments = computed(() => {
	const result: { type: 'text' | 'link' | 'code'; value: string }[] = []
	// match URLs or backtick-wrapped code
	const pattern = /(https?:\/\/[^\s<>`]+)|`([^`]+)`/g
	let lastIndex = 0
	let match: RegExpExecArray | null

	while ((match = pattern.exec(props.text)) !== null) {
		if (match.index > lastIndex) {
			result.push({
				type: 'text',
				value: props.text.slice(lastIndex, match.index),
			})
		}
		if (match[1]) {
			result.push({ type: 'link', value: match[1] })
		} else if (match[2]) {
			result.push({ type: 'code', value: match[2] })
		}
		lastIndex = pattern.lastIndex
	}

	if (lastIndex < props.text.length) {
		result.push({ type: 'text', value: props.text.slice(lastIndex) })
	}

	return result
})
</script>

<template>
	<template v-for="(seg, i) in segments" :key="i">
		<a
			v-if="seg.type === 'link'"
			:href="seg.value"
			target="_blank"
			rel="noopener noreferrer"
			class="font-medium underline"
			>{{ seg.value }}</a
		>
		<code
			v-else-if="seg.type === 'code'"
			class="rounded bg-surface-gray-3 px-1 py-0.5 font-mono text-[0.9em] text-ink-gray-8"
			>{{ seg.value }}</code
		>
		<template v-else>{{ seg.value }}</template>
	</template>
</template>
