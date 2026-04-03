<script setup lang="ts">
import { onMounted, useTemplateRef, computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import LucideX from '~icons/lucide/x';
import LucideSearch from '~icons/lucide/search';

import { formatLabels, filterLabels } from './utils';

const emits = defineEmits<{ close: [] }>();

const searchQuery = ref('');
const inputRef = useTemplateRef<HTMLInputElement>('inputRef');

import { searchModalOpen } from '@/data/ui';

const close = () => (searchModalOpen.value = false);

onMounted(() => {
	inputRef.value?.focus();
});

const router = useRouter();

const initialData = router.getRoutes();

const rawList = computed(() => formatLabels(initialData));

const list = computed(() => {
	return filterLabels(rawList.value, searchQuery.value);
});

watch(searchQuery, () => {
	const filtered = filterLabels(list.value, searchQuery.value);
	list.value = filtered;
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
					v-model="searchQuery"
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
			<div
				class="max-h-[55vh] min-h-[55vh] overflow-auto p-4 flex flex-col gap-2 text-sm"
				v-if="Object.keys(list).length > 0"
			>
				<template v-for="(v, k, i) in list">
					<!-- routes have hyphens usually so format -->
					<span class="text-ink-gray-4 font-mono uppercase mb-2">
						{{ k.split('-').join(' ') }}
					</span>

					<div class="flex flex-col gap-4 mb-5">
						<span v-for="item in v" class="">
							{{ item.name }}
						</span>
					</div>
				</template>
			</div>

			<div v-else class="flex my-5 p-4 text-ink-gray-5">
				<span class="flex items-center gap-2 mx-auto">
					<LucideFrown class="size-4" /> No results found
				</span>
			</div>
		</div>
	</div>
</template>

<style scoped>
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
