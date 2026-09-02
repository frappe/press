<script setup lang="ts">
import { computed } from 'vue'

interface Props {
	title: string
	type?: string
	button?: { label: string; link: string }
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
		<div class="prose-sm text-ink-gray-8" v-html="title" />
		<Button
			v-if="button"
			class="ml-auto shrink-0"
			variant="outline"
			:link="button.link"
		>
			{{ button.label }}
		</Button>
	</div>
</template>
