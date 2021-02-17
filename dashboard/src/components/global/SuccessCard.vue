<template>
	<div class="flex flex-col items-center p-10 text-base bg-white rounded-md">
		<GreenCheckIcon class="w-8 h-8" />
		<h2 class="mt-4 text-lg font-medium text-gray-900">
			{{ title }}
		</h2>
		<p class="text-base text-center text-gray-700 mt-1.5">
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
