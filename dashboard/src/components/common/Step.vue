<script setup lang="ts">
interface Props {
	label: string;
	class?: string;
}

defineProps<Props>();
</script>

<template>
	<div class="flex gap-4 items-start">
		<div class="flex flex-col items-center self-stretch">
			<div
				class="size-6 rounded-full border bg-surface-gray-2 flex items-center justify-center text-xs shrink-0"
			>
				{{ label }}
			</div>
			<div class="w-px grow bg-surface-gray-3"></div>
		</div>

		<div :class="class">
			<slot> </slot>
		</div>
	</div>
</template>
