<script setup>
import { AccordionContent } from 'reka-ui'

defineOptions({ inheritAttrs: false })
</script>

<template>
	<AccordionContent
		v-bind="$attrs"
		class="overflow-hidden text-pretty text-sm leading-relaxed text-ink-gray-6"
	>
		<div class="pb-4 pl-7 pr-1 pt-0">
			<slot />
		</div>
	</AccordionContent>
</template>
