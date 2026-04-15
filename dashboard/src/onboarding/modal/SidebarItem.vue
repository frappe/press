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
});
</script>

<template>
	<button
		class="w-full cursor-pointer rounded-md py-2.5 px-3 text-left text-base transition-all hover:bg-surface-white"
		:class="
			active
				? 'bg-surface-white font-medium text-ink-gray-9 shadow-xs border border-gray-100'
				: 'text-ink-gray-6 hover:bg-gray-100'
		"
	>
		{{ title }}
	</button>
</template>
