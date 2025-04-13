<template>
	<div
		@click="toggle"
		class="flex cursor-pointer select-none items-center rounded px-2 py-1.5 text-gray-800 transition hover:bg-gray-100"
		:class="[
			item.disabled ? 'pointer-events-none opacity-50' : '',
			$attrs.class
		]"
	>
		<div class="flex w-full items-center space-x-2">
			<span class="grid h-5 w-5 place-items-center">
				<component :is="item.icon" class="h-4 w-4 text-gray-500" />
			</span>
			<span class="text-base">{{ item.name }}</span>
			<span class="!ml-auto">
				<i-lucide-chevron-down v-if="isOpened" class="h-4 w-4 text-gray-500" />
				<i-lucide-chevron-right v-else class="h-4 w-4 text-gray-500" />
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
		required: true
	}
});

const isOpened = ref(false);

const toggle = () => {
	isOpened.value = !isOpened.value;
};

onMounted(() => {
	isOpened.value = props.item.isActive;
});
</script>
