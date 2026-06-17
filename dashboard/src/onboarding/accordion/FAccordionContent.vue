<script setup>
import { AccordionContent } from 'reka-ui'

defineOptions({ inheritAttrs: false })
</script>

<template>
	<AccordionContent
		v-bind="$attrs"
		class="faccordion-content overflow-hidden text-pretty text-sm leading-relaxed text-ink-gray-6"
	>
		<div class="pb-4 pl-7 pr-1 pt-0">
			<slot />
		</div>
	</AccordionContent>
</template>

<style scoped>
/*
 * Snappy, sub-300ms ease-out reveal
 */
.faccordion-content[data-state="open"] {
	animation: faccordion-down 220ms cubic-bezier(0.16, 1, 0.3, 1);
}

.faccordion-content[data-state="closed"] {
	animation: faccordion-up 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes faccordion-down {
	from {
		height: 0;
		opacity: 0;
	}

	to {
		height: var(--reka-accordion-content-height);
		opacity: 1;
	}
}

@keyframes faccordion-up {
	from {
		height: var(--reka-accordion-content-height);
		opacity: 1;
	}

	to {
		height: 0;
		opacity: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.faccordion-content[data-state="open"],
	.faccordion-content[data-state="closed"] {
		animation: none;
	}
}
</style>
