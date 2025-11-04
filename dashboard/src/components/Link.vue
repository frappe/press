<template>
	<component
		:is="to ? 'router-link' : 'a'"
		v-bind="to ? { to } : { href }"
		:class="{
			'text-gray-900 border-b border-gray-800 hover:text-gray-700 hover:border-gray-600 outline-gray-400':
				to || href,
			'': !(to || href),
		}"
	>
		<slot />
	</component>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';

defineProps<{
	href?: string;
	to?: string | Object;
}>();
</script>
