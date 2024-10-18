<template>
	<div class="m-5 h-full">
		<div class="mb-5 flex items-center space-x-4">
			<Button
				@click="$router.go(-1)"
				icon="arrow-left"
				label="Go Back"
			></Button>
			<h2 class="font-semibold">{{ title }}</h2>
		</div>

		<!-- body -->
		<slot></slot>
	</div>
</template>
<script>
export default {
	name: 'DatabasePageWrapper',
	props: ['title']
};
</script>
