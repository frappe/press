<template>
	<button
		class="focus:outline-none rounded-md py-2 px-4"
		@click="route && $router.push(route)"
		v-bind="$attrs"
		v-on="$listeners"
	>
		<slot></slot>
	</button>
</template>
<script>
export default {
	name: 'Button',
	props: ['route']
};
</script>
