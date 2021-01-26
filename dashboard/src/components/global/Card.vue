<template>
	<div class="px-6 py-5 bg-white border rounded-lg shadow">
		<div class="flex items-baseline justify-between">
			<h2 class="text-xl font-semibold">{{ title }}</h2>
			<div class="flex items-center space-x-2">
				<slot name="actions"></slot>
			</div>
		</div>
		<p class="text-base text-gray-600 mt-1.5" v-if="subtitle">
			{{ subtitle }}
		</p>
		<div class="mt-4">
			<slot></slot>
		</div>
	</div>
</template>
<script>
export default {
	name: 'Card',
	props: ['title', 'subtitle']
};
</script>
