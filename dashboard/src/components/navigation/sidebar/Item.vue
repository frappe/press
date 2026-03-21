<script setup lang="ts">
let props = defineProps({
	item: {
		type: Object,
		required: true,
	},
});
</script>

<template>
	<router-link custom v-slot="{ href, navigate }" :to="item.route">
		<a
			:href="href"
			@click="navigate"
			class="flex items-center rounded px-2 py-1 text-ink-gray-6 transition"
			:class="[
				item.isActive ? 'bg-surface-white shadow-sm' : 'hover:bg-gray-100',
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
			</div>
		</a>
	</router-link>
</template>
