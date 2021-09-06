<template>
	<div class="flex items-center justify-between py-3">
		<div>
			<h3 class="text-base font-medium text-gray-900">
				{{ title }}
			</h3>
			<div class="mt-1" v-if="subtitle || description || $slots.subtitle">
				<template v-if="subtitle || description">
					<span class="text-base text-gray-600">
						{{ subtitle || description }}
					</span>
				</template>
				<slot v-if="$slots.subtitle" name="subtitle" />
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
