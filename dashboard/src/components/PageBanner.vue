<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeHtml } from '@/utils/format'

interface Props {
	title: string
	type?: string
	// Spread onto Button, so link, onClick and variant all come through
	button?: Record<string, unknown>
}

const props = withDefaults(defineProps<Props>(), { type: 'warning' })

const colors: Record<string, { bg: string; icon: string }> = {
	info: { bg: 'bg-surface-blue-2', icon: 'text-ink-blue-3' },
	success: { bg: 'bg-surface-green-2', icon: 'text-ink-green-3' },
	warning: { bg: 'bg-surface-amber-2', icon: 'text-ink-amber-3' },
	error: { bg: 'bg-surface-red-2', icon: 'text-ink-red-3' },
	general: { bg: 'bg-surface-gray-2', icon: 'text-ink-gray-5' },
}

// An unknown type must not take the page down with it
const color = computed(() => colors[props.type] ?? colors.general)

// Titles are written in code today, but the markup they carry is worth <b> only.
// Sanitizing here keeps a future title built from a document field harmless.
const safeTitle = computed(() => sanitizeHtml(props.title))
</script>

<template>
	<div
		class="flex items-center gap-2 border-b px-2 py-1.5 md:px-5"
		:class="color.bg"
	>
		<lucide-alert-triangle
			v-if="type === 'error' || type === 'warning'"
			class="size-4 shrink-0"
			:class="color.icon"
		/>
		<lucide-info v-else class="size-4 shrink-0" :class="color.icon" />
		<div class="prose-sm text-ink-gray-8" v-html="safeTitle" />
		<Button v-if="button" v-bind="button" class="ml-auto shrink-0" />
	</div>
</template>
