<script setup lang="ts">
import { ref, watch } from 'vue';
import Item from './Item.vue';
import LucideChevronRight from '~icons/lucide/chevron-right';
import CollapseTransition from '@/components/utils/CollapseTransition.vue';

let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});

const isOpened = ref(false);

const toggle = () => {
	isOpened.value = !isOpened.value;
};

watch(
	() => props.item.isActive,
	() => {
		isOpened.value = props.item.isActive;
	},
);
</script>

<template>
	<div
		@click="toggle"
		class="mt-0.5 flex cursor-pointer select-none items-center rounded px-2 py-1 text-ink-gray-6 transition hover:bg-gray-100"
		:class="[
			item.disabled ? 'pointer-events-none opacity-50' : '',
			$attrs.class,
		]"
	>
		<div class="flex w-full items-center space-x-2">
			<span class="grid h-5 w-6 place-items-center">
				<component :is="item.icon" class="h-4 w-4 text-ink-gray-6" />
			</span>
			<span class="text-sm">{{ item.name }}</span>
			<component :is="item.badge" />
			<span class="!ml-auto">
				<LucideChevronRight
					class="size-4 text-gray-500 transition-transform duration-200"
					:class="{ 'rotate-90': isOpened }"
				/>
			</span>
		</div>
	</div>
	<CollapseTransition>
		<div v-if="isOpened">
			<div class="ml-5 py-1">
				<Item
					v-for="(subItem, i) in item.children"
					:class="{ 'mt-0.5': i !== 0 }"
					:key="subItem.name"
					:item="subItem"
				/>
			</div>
		</div>
	</CollapseTransition>
</template>
