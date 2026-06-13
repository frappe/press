<script setup>
import { AccordionTrigger } from 'reka-ui'

defineOptions({ inheritAttrs: false })
</script>

<template>
	<AccordionTrigger
		v-bind="$attrs"
		class="group flex w-full items-center gap-3 border-0 bg-transparent py-4 text-left text-base-medium text-ink-gray-8 outline-none ring-inset transition-colors focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:opacity-60"
	>
		<slot />
	</AccordionTrigger>
</template>
