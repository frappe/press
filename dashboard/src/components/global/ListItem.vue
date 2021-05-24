<template>
	<div class="flex items-center justify-between py-3">
		<div>
			<h3 class="text-base font-medium text-gray-900">
				{{ title }}
			</h3>
			<div class="mt-1 text-base text-gray-600" v-if="subtitle || description">
				{{ subtitle || description }}
			</div>
		</div>
		<slot name="actions"></slot>
	</div>
</template>
<script>
export default {
	name: 'ListItem',
	props: ['title', 'subtitle', 'description']
};
</script>
