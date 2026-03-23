<template>
	<component
		:is="to ? 'router-link' : 'a'"
		v-bind="to ? { to } : { href }"
		:class="{
			'text-ink-gray-9 border-b border-gray-800 hover:text-ink-gray-7 hover:border-gray-600 outline-gray-400':
				to || href,
		}"
	>
		<slot />
	</component>
</template>

<script setup lang="ts">
defineProps<{
	href?: string;
	to?: string | object;
}>();
</script>
