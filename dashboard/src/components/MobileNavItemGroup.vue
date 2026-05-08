<template>
	<div
		@click="toggle"
		class="flex cursor-pointer select-none items-center rounded px-2 py-1.5 text-ink-gray-8 transition hover:bg-surface-gray-2"
		:class="[
			item.disabled ? 'pointer-events-none opacity-50' : '',
			$attrs.class,
		]"
	>
		<div class="flex w-full items-center space-x-2">
			<span class="grid h-5 w-5 place-items-center">
				<component :is="item.icon" class="h-4 w-4 text-ink-gray-5" />
			</span>
			<span class="text-base">{{ item.name }}</span>
			<span class="!ml-auto">
				<lucide-chevron-down v-if="isOpened" class="h-4 w-4 text-ink-gray-5" />
				<lucide-chevron-right v-else class="h-4 w-4 text-ink-gray-5" />
			</span>
		</div>
	</div>
	<div class="ml-5 py-1" v-if="isOpened">
		<MobileNavItem
			v-for="subItem in item.children"
			:key="subItem.name"
			:item="subItem"
		/>
	</div>
</template>
<script setup>
import { onMounted, ref, watch } from 'vue';
import MobileNavItem from './MobileNavItem.vue';

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

onMounted(() => {
	isOpened.value = props.item.isActive;
});
</script>
