<script setup lang="ts">
import {
	ScrollAreaRoot,
	ScrollAreaViewport,
	ScrollAreaThumb,
	ScrollAreaScrollbar,
} from 'reka-ui';
</script>

<template>
	<ScrollAreaRoot
		class="relative overflow-hidden"
		style="--scrollbar-size: 10px"
		:scroll-hide-delay="0"
	>
		<ScrollAreaViewport class="w-full h-full">
			<slot />
		</ScrollAreaViewport>

		<ScrollAreaScrollbar
			class="flex select-none touch-none p-0.5 z-20 transition-colors duration-[160ms] ease-out data-[orientation=vertical]:w-2.5"
			orientation="vertical"
		>
			<ScrollAreaThumb
				class="flex-1 bg-surface-gray-3 rounded-[10px] relative before:content-[''] before:absolute before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:w-full before:h-full before:min-w-[44px] before:min-h-[44px]"
			/>
		</ScrollAreaScrollbar>
	</ScrollAreaRoot>
</template>
