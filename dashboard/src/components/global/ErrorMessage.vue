<template>
	<div
		v-if="error"
		class="whitespace-pre-line text-sm text-red-600"
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
