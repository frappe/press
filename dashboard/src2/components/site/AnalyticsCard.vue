<template>
	<div class="rounded-md border">
		<div class="flex h-12 items-center justify-between border-b px-5">
			<h3 class="text-lg font-medium text-gray-900">{{ title }}</h3>
			<slot name="action"></slot>
		</div>
		<slot></slot>
	</div>
</template>

<script>
export default {
	name: 'AnalyticsCard',
	props: ['title']
};
</script>
