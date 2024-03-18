<template>
	<div
		class="h-screen max-w-none shrink-0 overflow-hidden bg-white"
		v-if="saasProduct"
	>
		<div v-html="saasProduct.description" />
	</div>
</template>
<script>
export default {
	name: 'ProductSignupPitch',
	props: {
		saasProduct: {
			type: Object,
			required: true
		}
	}
};
</script>
