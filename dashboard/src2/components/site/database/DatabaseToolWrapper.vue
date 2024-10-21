<template>
	<div class="m-5 h-full items-center justify-center">
		<div class="mb-5 flex flex-row items-center justify-between">
			<!-- Title and back button -->
			<div class="flex items-center space-x-4">
				<Button
					@click="$router.go(-1)"
					icon="arrow-left"
					label="Go Back"
				></Button>
				<h2 class="font-semibold">{{ title }}</h2>
			</div>
			<slot name="actions"></slot>
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
