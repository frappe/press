<template>
	<div class="shrink-0 bg-white" v-if="saasProduct">
		<div
			class="prose prose-sm mt-4 max-w-none"
			v-html="saasProduct.description"
		/>
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
