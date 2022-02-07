<template>
	<div
		v-if="success"
		class="whitespace-pre-line text-sm text-green-600"
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
