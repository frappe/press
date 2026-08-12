<script setup>
import { AccordionHeader } from 'reka-ui';

defineOptions({ inheritAttrs: false });
</script>

<template>
	<AccordionHeader v-bind="$attrs" class="m-0">
		<slot />
	</AccordionHeader>
</template>
