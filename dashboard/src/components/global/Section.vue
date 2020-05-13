<template>
	<section>
		<h2 class="text-lg font-medium">{{ title }}</h2>
		<p class="text-gray-600" v-if="description">
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
