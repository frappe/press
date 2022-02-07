<template>
	<button
		class="cursor-pointer rounded-lg border border-gray-100 px-4 py-2 text-left shadow focus:outline-none"
		:class="
			selected ? 'bg-blue-50 ring-2 ring-blue-500' : 'hover:border-gray-300'
		"
	>
		<div class="flex items-center">
			<img
				v-if="image"
				:src="image"
				:alt="title"
				class="mr-4 h-10 w-10"
				:class="[fullCircleImage ? 'rounded-full' : 'rounded-lg']"
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
	props: ['selected', 'title', 'image', 'fullCircleImage']
};
</script>
