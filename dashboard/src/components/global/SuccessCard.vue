<template>
	<div class="flex flex-col rounded-md border bg-white p-10 shadow-sm">
		<div class="flex items-center">
			<GreenCheckIcon class="mr-2 h-5 w-5" />
			<h2 class="text-lg font-medium text-gray-900">
				{{ title }}
			</h2>
		</div>
		<p class="mt-3 text-p-base text-gray-700">
			<slot></slot>
		</p>
	</div>
</template>

<script>
export default {
	name: 'SuccessCard',
	props: ['title', 'message']
};
</script>
