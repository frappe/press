<template>
	<div class="shrink-0 bg-white" v-if="saasProduct">
		<div class="max-w-[480px]">
			<div class="prose prose-sm mt-4" v-html="saasProduct.description" />
		</div>
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
