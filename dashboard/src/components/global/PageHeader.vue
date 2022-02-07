<template>
	<div class="flex items-center justify-between bg-white px-4 sm:px-8">
		<div class="text-3xl font-bold">
			<slot name="title" />
		</div>
		<div class="flex items-center">
			<slot name="actions" />
		</div>
	</div>
</template>
