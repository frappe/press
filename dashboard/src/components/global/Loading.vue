<template>
	<div class="flex items-center text-base text-gray-500">
		<LoadingIndicator /> {{ text }}
	</div>
</template>
<script>
export default {
	name: 'Loading',
	props: {
		text: {
			type: String,
			default: 'Loading...'
		}
	}
};
</script>
