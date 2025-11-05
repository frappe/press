<template>
	<component
		:is="to ? 'router-link' : 'a'"
		v-bind="to ? { to } : { href }"
		:class="{
			'text-gray-900 border-b border-gray-800 hover:text-gray-700 hover:border-gray-600 outline-gray-400':
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
