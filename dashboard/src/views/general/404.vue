<template>
	<div class="flex h-screen flex-col items-center justify-center p-5">
		<div class="text-[4rem] text-gray-900">404</div>
		<div class="text-base text-gray-600">Page not found</div>
		<Button class="mt-4" route="/sites" variant="outline">
			Go to Site list
		</Button>
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
