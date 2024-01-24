<template>
	<router-link custom v-slot="{ href, navigate }" :to="item.route">
		<a
			:href="href"
			@click="navigate"
			class="flex items-center rounded px-2 py-1 text-gray-800 transition"
			:class="[
				item.isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100',
				item.disabled ? 'pointer-events-none opacity-50' : '',
				$attrs.class
			]"
		>
			<div class="flex w-full items-center space-x-2">
				<span class="grid h-5 w-6 place-items-center">
					<component :is="item.icon" class="h-4 w-4 text-gray-500" />
				</span>
				<span class="text-sm">{{ item.name }}</span>
			</div>
		</a>
	</router-link>
</template>

<script setup>
let props = defineProps({
	item: {
		type: Object,
		required: true
	}
});
</script>
