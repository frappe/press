<template>
	<div class="py-4 px-8 flex justify-between items-center">
		<div class="font-semibold text-xl">
			<slot name="title" />
		</div>
		<div class="flex items-stretch ">
			<slot name="actions" />
		</div>
	</div>
</template>
