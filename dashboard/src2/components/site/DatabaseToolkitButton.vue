<template>
	<div class="py-3 first:pt-0 last:pb-0">
		<div class="flex items-center justify-between gap-1">
			<div>
				<h3 class="text-base font-medium">{{ details.label }}</h3>
				<p class="mt-1 text-p-base text-gray-600">
					{{ details.description }}
				</p>
			</div>
			<Button class="whitespace-nowrap" @click="onClick(details)">
				<p class="text-gray-800">{{ details.buttonLabel }}</p>
			</Button>
		</div>
	</div>
</template>
<script>
export default {
	name: 'DatabaseToolkitButton',
	props: ['details', 'onClick']
};
</script>
