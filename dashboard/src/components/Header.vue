<template>
	<header
		class="border-b bg-surface-white p-2 md:px-5 md:py-2.5"
		:class="{ 'sticky top-0 z-10': sticky }"
	>
		<div class="flex items-center justify-between sm:h-7">
			<slot />
		</div>
	</header>
</template>

<script setup>
defineProps({
	sticky: {
		type: Boolean,
		default: false,
	},
});
</script>
