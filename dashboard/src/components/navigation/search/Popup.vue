<script setup lang="ts">
import { onMounted, useTemplateRef, computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import LucideX from '~icons/lucide/x';
import LucideSearch from '~icons/lucide/search';

import { filterLabels } from './utils';
import { index } from './index';

const emits = defineEmits<{ close: [] }>();

const searchQuery = ref('');
const inputRef = useTemplateRef<HTMLInputElement>('inputRef');

import { searchModalOpen } from '@/data/ui';

const close = () => (searchModalOpen.value = false);

onMounted(() => {
	inputRef.value?.focus();
});

const router = useRouter();

// filter
const list = ref(index.value);

const flatList = computed(() =>
	Object.values(list.value).flatMap((v) => v.items),
);

watch(searchQuery, () => {
	const filtered = filterLabels(index.value, searchQuery.value);
	list.value = filtered;

	const optionEls = document
		.getElementById('search-results')
		?.querySelectorAll('[role="option"]');
	if (optionEls) optionEls.value = optionEls;

	navigationIndex.value = 0;
});

// arrow up/down navigation
const navigationIndex = ref(0);

const navigateEnter = (close) => {
	const item = flatList.value[navigationIndex.value];
	if (item) {
		router.push(item.route);
		close();
	}
};

const navigateUp = () => {
	if (navigationIndex.value > 0) {
		navigationIndex.value--;
	}
};

const navigateDown = () => {
	if (navigationIndex.value < flatList.value.length - 1) {
		navigationIndex.value++;
	}
};

watch(navigationIndex, () => {
	const els = document
		.getElementById('search-results')
		?.querySelectorAll('[role="option"]');

	els?.[navigationIndex.value]?.scrollIntoView({ block: 'center' });
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
			@keydown.enter.prevent="navigateEnter(close)"
		>
			<!-- input -->
			<div class="flex gap-2 items-center border-b border-outline-gray-2 p-3">
				<LucideSearch class="size-4" />

				<input
					ref="inputRef"
					placeholder="Search"
					class="w-full bg-transparent !outline-none !border-0 text-sm p-0 !ring-0"
					autofocus
					@keydown.up.prevent="navigateUp"
					@keydown.down.prevent="navigateDown"
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
				class="max-h-[42vh] min-h-[42vh] overflow-y-scroll p-2 flex flex-col text-sm"
				id="search-results"
				role="listbox"
				v-if="Object.keys(list).length > 0"
			>
				<template v-for="(v, k, i) in list">
					<!-- routes have hyphens usually so format -->
					<span class="text-ink-gray-4 font-mono uppercase p-2">
						{{ k.split('-').join(' ') }}
					</span>

					<div class="flex flex-col mb-3">
						<router-link
							v-for="item in v.items"
							:key="item.route"
							role="option"
							:to="item.route"
							@click="close"
							class="hover:bg-surface-gray-2 p-2 rounded flex gap-2 items-center"
							:class="{
								'bg-surface-gray-2': navigationIndex === flatList.indexOf(item),
							}"
						>
							<component :is="item.icon || LucideDot" class="size-4" />

							{{ item.name }}
						</router-link>
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
