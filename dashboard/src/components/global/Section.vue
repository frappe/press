<template>
	<section>
		<h2 class="text-lg font-semibold">{{ title }}</h2>
		<p class="text-base text-gray-600" v-if="description">
			{{ description }}
		</p>
		<div class="mt-6">
			<slot />
		</div>
	</section>
</template>

<script>
export default {
	name: 'Section',
	props: ['title', 'description']
};
</script>
