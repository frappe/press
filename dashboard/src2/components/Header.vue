<template>
	<header
		class="border-b bg-white px-5 py-2.5 sm:px-5"
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
		default: false
	}
});
</script>
