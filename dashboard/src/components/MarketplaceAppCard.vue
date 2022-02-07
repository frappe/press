<template>
	<button
		class="flex self-stretch rounded-lg border bg-white p-3 shadow hover:border-gray-300 focus:outline-none"
	>
		<Avatar
			class="shrink-0"
			size="lg"
			shape="square"
			:imageURL="app.image"
			:label="app.title"
		/>
		<div class="ml-3 w-full">
			<div class="flex items-center justify-between">
				<h2 class="text-left text-xl font-bold">
					{{ app.title }}
				</h2>
				<Badge :status="app.status">{{ app.status }}</Badge>
			</div>
			<p class="pt-1 text-left text-base text-gray-600">
				{{ app.description }}
			</p>
		</div>
	</button>
</template>

<script>
export default {
	props: ['app']
};
</script>
