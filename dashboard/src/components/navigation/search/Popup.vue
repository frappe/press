<script setup lang="ts">
import { onMounted, useTemplateRef } from 'vue';

import LucideX from '~icons/lucide/x';
import LucideSearch from '~icons/lucide/search';

const emits = defineEmits<{ close: [] }>();

const inputRef = useTemplateRef<HTMLInputElement>('inputRef');
import { searchModalOpen } from '@/data/ui';
const close = () => (searchModalOpen.value = false);

onMounted(() => {
	inputRef.value?.focus();
});
</script>

<template>
	<div
		class="fixed inset-0 z-100 flex items-start justify-center bg-black/50 backdrop-blur-sm backdrop-enter"
		@click.self="close"
	>
		<div
			class="mt-[15vh] w-full max-w-lg overflow-hidden rounded bg-surface-cards shadow-lg modal-enter"
			@keydown.esc.prevent="close"
		>
			<!-- input -->
			<div class="flex gap-2 items-center border-b border-outline-gray-2 p-3">
				<LucideSearch class="size-4" />

				<input
					ref="inputRef"
					placeholder="Search"
					class="w-full bg-transparent !outline-none !border-0 text-sm p-0 !ring-0"
					autofocus
				/>

				<button
					class="text-muted-foreground hover:text-foreground"
					aria-label="Close"
					@click="close"
				>
					<LucideX class="size-4" />
				</button>
			</div>

			<!-- results -->
			<ul ref="resultsEl" class="max-h-[55vh] min-h-[55vh] overflow-auto" ``>
				hii
			</ul>
		</div>
	</div>
</template>

<style>
@keyframes backdropIn {
	from {
		opacity: 0;
	}

	to {
		opacity: 1;
	}
}

@keyframes modalIn {
	from {
		opacity: 0;
		transform: translateY(-18px) scale(0.97);
	}

	to {
		opacity: 1;
		transform: translateY(0) scale(1);
	}
}

.backdrop-enter {
	animation: backdropIn 0.18s ease both;
}

.modal-enter {
	animation: modalIn 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
}
</style>
