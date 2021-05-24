<template>
	<button
		class="px-4 py-2 text-left border border-gray-100 rounded-lg shadow cursor-pointer focus:outline-none"
		:class="
			selected ? 'bg-blue-50 ring-2 ring-blue-500' : 'hover:border-gray-300'
		"
	>
		<div class="flex items-center">
			<img
				v-if="image"
				:src="image"
				:alt="title"
				class="w-10 h-10 mr-4 rounded-full"
			/>
			<div class="my-1">
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
