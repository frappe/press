<script setup>
defineProps({
	title: {
		type: String,
		default: '',
	},
	html: {
		type: String,
		default: '',
	},
});
</script>

<template>
	<div
		class="rounded-md border-px border-gray-4 bg-surface-white px-4 py-3 text-sm leading-5 shadow-2xl"
	>
		<div v-if="title" class="mb-1 font-semibold text-ink-gray-9">
			{{ title }}
		</div>

		<!-- Dangerous HTML rendering -->
		<div v-if="html" class="text-ink-gray-6" v-html="html" />
	</div>
</template>
