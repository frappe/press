<template>
	<div
		class="flex items-center whitespace-nowrap px-3 py-3 text-base text-gray-800"
	>
		<slot />
	</div>
</template>

<script>
export default {
	name: 'TableCell',
	inject: ['columns']
};
</script>
