<template>
	<div
		v-if="success"
		class="text-sm text-green-600 whitespace-pre-line"
		role="success"
		v-html="success"
	></div>
</template>

<script>
export default {
	name: 'SuccessMessage',
	props: ['success']
};
</script>
