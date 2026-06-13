<script setup>
defineProps({
	title: {
		type: String,
		required: true,
	},
	active: {
		type: Boolean,
		default: false,
	},
})
</script>

<template>
	<button
		class="w-full cursor-pointer rounded-md px-3 py-2.5 text-left text-base transition-colors"
		:class="
			active
				? 'border border-outline-gray-2 bg-surface-base font-medium text-ink-gray-9 shadow-xs'
				: 'border border-transparent text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-8'
		"
	>
		{{ title }}
	</button>
</template>
