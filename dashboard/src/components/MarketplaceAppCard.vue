<template>
	<button
		class="flex p-3 bg-white border rounded-lg shadow self-stretch focus:outline-none hover:border-gray-300"
	>
		<Avatar
			class="flex-shrink-0"
			size="lg"
			shape="square"
			:imageURL="app.image"
			:label="app.title"
		/>
		<div class="ml-3 w-full">
			<div class="flex items-center justify-between">
				<h2 class="text-xl text-left font-bold">
					{{ app.title }}
				</h2>
				<Badge :status="app.status">{{ app.status }}</Badge>
			</div>
			<p class="text-base text-left text-gray-600 pt-1">
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
