<template>
	<div class="flex flex-col rounded-lg border shadow md:flex-row">
		<Card
			:title="title"
			:subtitle="subtitle"
			class="w-full rounded-none border-none shadow-none md:w-1/3"
			:class="{ 'hidden md:flex': showDetails }"
			:style="{ height: viewportWidth > 768 ? 'calc(100vh - 16rem)' : null }"
		>
			<slot></slot>
		</Card>
		<slot name="details"></slot>
	</div>
</template>
<script>
export default {
	name: 'CardWithDetails',
	props: ['title', 'subtitle', 'showDetails'],
	inject: ['viewportWidth']
};
</script>
