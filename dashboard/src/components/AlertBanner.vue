<script setup lang="ts">
interface Props {
	title?: string;
	type?: string;
	showIcon?: boolean;
	isDismissible?: number;
}

const props = withDefaults(defineProps<Props>(), {
	showIcon: true,
	type: 'info',
});

const emit = defineEmits<{
	(e: 'dismissBanner'): void;
}>();

const colors = {
	info: { bg: 'bg-surface-blue-2', text: 'text-ink-blue-3' },
	success: { bg: 'bg-surface-green-2', text: 'text-ink-green-3' },
	error: { bg: 'bg-surface-red-2', text: 'text-ink-red-3' },
	warning: { bg: 'bg-surface-amber-2', text: 'text-ink-amber-3' },
	general: { bg: 'bg-surface-gray-2', text: 'text-ink-gray-3' },
};
</script>

<template>
	<div
		class="flex items-center justify-between rounded-md p-2"
		:class="colors[type].bg"
	>
		<div class="flex items-center gap-2.5">
			<lucide-alert-triangle
				v-if="showIcon && (type === 'error' || type === 'warning')"
				class="ml-1 size-4 shrink-0"
				:class="colors[type].text"
			/>
			<lucide-info
				v-if="showIcon && type === 'info'"
				class="ml-1 size-4 shrink-0"
				:class="colors[type].text"
			/>
			<div class="prose-sm font-medium text-ink-gray-8" v-html="title" />
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
					@click="$emit('dismissBanner')"
				>
					<template #icon>
						<lucide-x class="size-4" />
					</template>
				</Button>
			</div>
		</div>
	</div>
</template>
