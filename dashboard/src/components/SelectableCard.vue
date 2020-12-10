<template>
	<button
		class="px-4 py-2 text-left border border-gray-100 rounded-lg shadow cursor-pointer"
		:class="
			selected ? 'border-blue-500 shadow-outline-blue' : 'hover:border-gray-300'
		"
	>
		<div class="flex items-center">
			<img :src="image" :alt="title" class="w-10 h-10 rounded-full" />
			<div class="my-1 ml-4">
				<h3 class="text-lg font-bold text-gray-900">
					{{ title }}
				</h3>
				<slot name="secondary-content"></slot>
			</div>
		</div>
	</button>
</template>
<script>
export default {
	name: 'SelectableCard',
	props: ['selected', 'title', 'image']
};
</script>
