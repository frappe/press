<script setup>
import { AccordionRoot } from 'reka-ui'

/**
 * Styled Accordion root (Reka UI). Pair with FAccordionItem / FAccordionHeader /
 * FAccordionTrigger / FAccordionContent. Intended to mirror future frappe-ui API.
 */
defineOptions({ inheritAttrs: false })
</script>

<template>
	<AccordionRoot v-bind="$attrs" type="single" collapsible class="w-full">
		<slot />
	</AccordionRoot>
</template>
