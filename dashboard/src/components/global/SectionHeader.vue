<script setup>
const props = defineProps(['heading']);
</script>

<template>
	<div class="flex flex-row items-center justify-between">
		<h2 class="text-xl font-semibold text-ink-gray-8">{{ heading }}</h2>
		<slot name="actions"> </slot>
	</div>
</template>
