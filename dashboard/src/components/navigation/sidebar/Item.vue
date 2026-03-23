<script setup lang="ts">
let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});
</script>

<template>
	<router-link
		:to="item.route"
		class="flex items-center rounded px-2 py-1 text-ink-gray-6 transition space-x-2"
		:class="[
			item.isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100',
			item.disabled ? 'pointer-events-none opacity-50' : '',
			$attrs.class,
		]"
	>
		<span class="grid h-5 w-6 place-items-center">
			<component :is="item.icon" class="h-4 w-4 text-ink-gray-6" />
		</span>
		<span class="text-sm">{{ item.name }}</span>
		<component :is="item.badge" />
	</router-link>
	<div v-if="item.spacer" class="h-[10px] w-full" />
</template>
