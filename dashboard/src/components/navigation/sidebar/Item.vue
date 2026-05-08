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
		class="flex items-center rounded px-2 py-1.5 text-ink-gray-6 transition gap-2"
		:class="[
			item.isActive
				? 'bg-white dark:bg-surface-gray-2 text-ink-gray-8 shadow-sm'
				: 'hover:bg-surface-gray-2',
			item.disabled ? 'pointer-events-none opacity-50' : '',
			$attrs.class,
		]"
	>
		<component
			:is="item.icon"
			class="size-4 text-ink-gray-6"
			:class="item.isActive ? 'text-ink-gray-8' : ''"
		/>
		<span class="text-sm">{{ item.name }}</span>
		<component :is="item.badge" />
	</router-link>
</template>
