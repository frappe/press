<template>
	<div class="flex flex-col rounded-lg border md:flex-row">
		<Card
			:title="title"
			:subtitle="subtitle"
			class="w-full border-none shadow-none md:w-1/3"
			:class="{ 'hidden md:flex': showDetails }"
			:style="{ height: viewportWidth > 768 ? 'calc(100vh - 12rem)' : null }"
		>
			<slot></slot>
			<template #actions>
				<slot name="actions"></slot>
			</template>
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
