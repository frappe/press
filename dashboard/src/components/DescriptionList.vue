<template>
	<div class="space-y-4">
		<div v-for="item in items" :key="item.label">
			<div class="text-sm text-gray-700">{{ item.label }}</div>
			<div class="mt-1 rounded bg-gray-100 px-3 py-1 text-base text-gray-900">
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
