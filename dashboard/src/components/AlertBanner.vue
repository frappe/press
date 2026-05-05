<template>
	<div
		:class="`flex items-center justify-between rounded-md bg-${color}-100 p-2`"
	>
		<div class="flex items-center gap-2.5">
			<lucide-alert-triangle
				v-if="showIcon && (type === 'error' || type === 'warning')"
				:class="`ml-1 size-4 text-${color}-600 shrink-0`"
			/>
			<lucide-info
				v-if="showIcon && type === 'info'"
				:class="`ml-1 size-4 text-${color}-600 shrink-0`"
			/>
			<div class="prose-sm font-medium text-gray-800" v-html="title" />
		</div>

		<div class="flex items-center">
			<!-- Button Slot -->
			<slot></slot>

			<div
				class="flex items-center justify-center overflow-hidden rounded-sm"
				v-if="isDismissible"
			>
				<Button
					class="ml-1 transition-colors focus:outline-none text-ink-gray-8 bg-gray-700 bg-opacity-0 hover:bg-opacity-[4%] active:bg-opacity-[8%] h-7 w-7 rounded"
					variant="ghost"
					theme="colors"
					@click="$emit('dismissBanner')"
				>
					<template #icon>
						<lucide-x class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const colors: Record<string, string> = {
	info: 'blue',
	success: 'green',
	error: 'red',
	warning: 'amber',
	general: 'gray',
};

const props = defineProps<{
	title?: string;
	type?: string;
	showIcon?: boolean;
	isDismissible?: number;
}>();

const emit = defineEmits<{
	(e: 'dismissBanner'): void;
}>();

const color = computed(() => {
	return colors[props.type ?? 'info'] ?? 'gray';
});
</script>
