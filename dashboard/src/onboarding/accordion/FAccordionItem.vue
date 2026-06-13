<script setup>
import { AccordionItem } from 'reka-ui'

defineOptions({ inheritAttrs: false })
</script>

<template>
	<AccordionItem v-bind="$attrs">
		<slot />
	</AccordionItem>
</template>
