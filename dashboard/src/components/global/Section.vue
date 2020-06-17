<template>
	<section>
		<h2 class="text-xl font-medium text-gray-900">{{ title }}</h2>
		<p class="text-base text-gray-500" v-if="description">
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
