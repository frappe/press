<template>
	<div
		class="flex shrink-0 justify-center bg-white px-10 pt-32"
		v-if="saasProduct"
	>
		<div class="max-w-[480px]">
			<div class="flex items-center justify-center space-x-2">
				<img :src="saasProduct.logo" :alt="saasProduct.title" class="h-7" />
				<h1 class="text-center text-2xl font-semibold tracking-tight">
					{{ saasProduct.title }}
				</h1>
			</div>
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
