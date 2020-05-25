<template>
	<div
		v-if="error"
		class="text-sm text-red-600 whitespace-pre-line"
		role="alert"
		v-html="error"
	></div>
</template>

<script>
export default {
	name: 'ErrorMessage',
	props: ['error']
};
</script>
