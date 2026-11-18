<template>
	<div
		class="flex size-7 shrink-0 items-center justify-center rounded-full text-base font-medium"
		:class="classes[state]"
	>
		<LucideCheck v-if="state === 'done'" class="size-4" />
		<template v-else>{{ number }}</template>
	</div>
</template>

<script setup>
// A numbered step: done shows a tick, current is filled, next is outlined.
defineProps({
	number: { type: Number, required: true },
	state: { type: String, required: true },
})

const classes = {
	done: 'bg-surface-green-3 text-ink-white',
	current: 'bg-surface-gray-7 text-ink-white',
	next: 'border border-outline-gray-3 text-ink-gray-6',
}
</script>
