<template>
	<div class="space-y-4">
		<div v-for="item in items" :key="item.label">
			<div class="text-sm text-gray-700">{{ item.label }}</div>
			<div class="px-3 py-1 mt-1 text-base text-gray-900 bg-gray-100 rounded">
				{{ item.value }}
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'DescriptionList',
	props: ['items']
};
</script>
