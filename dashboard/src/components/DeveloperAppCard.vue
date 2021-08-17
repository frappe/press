<template>
	<button
		:key="app.name"
		class="
					text-left border 
					border-gray-100 
					rounded-lg shadow 
					cursor-pointer 
					focus:outline-none hover:border-gray-300
					"
	>
		<div class="px-3 py-2 grid grid-cols-4 items-center">
			<img
				class="border border-1 border-gray-300 h-12 w-12 object-contain rounded"
				:src="app.image"
				:alt="`${app.name} Logo`"
			/>
			<div class="col-span-3 flex flex-col items-stretch justify-between">
				<div
					class="mb-2 self-stretch flex flex-row justify-between items-start"
				>
					<h3 class="text-lg font-bold">{{ app.title }}</h3>
					<Badge :status="app.status">{{ app.status }}</Badge>
				</div>
				<p class="text-base text-gray-700">{{ app.description }}</p>
			</div>
		</div>
	</button>
</template>

<script>
export default {
	props: ['app']
};
</script>
