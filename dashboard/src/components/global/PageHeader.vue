<template>
	<div class="flex items-center justify-between px-4 py-4 bg-white sm:px-8">
		<div class="text-2xl font-bold">
			<slot name="title" />
		</div>
		<div class="flex items-stretch ">
			<slot name="actions" />
		</div>
	</div>
</template>
