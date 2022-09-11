<template>
	<div class="flex items-center justify-center">
		<div class="flex flex-col items-center">
			<span class="text-8xl" @dblclick="() => (surprise = true)">
				{{ surprise ? '😉' : '👀' }}
			</span>
			<h2 class="mt-5 text-5xl font-bold text-gray-900">Not Found</h2>
			<h3 class="text-lg font-semibold text-gray-700">
				Maybe someone gave you a wrong address?
			</h3>
		</div>
	</div>
</template>

<script>
export default {
	name: '404NotFound',
	data() {
		return {
			surprise: false
		};
	}
};
</script>
