<template>
	<button
		class="focus:outline-none rounded-md py-2 px-4"
		:class="{
			'opacity-50 cursor-not-allowed pointer-events-none': disabled
		}"
		@click="route && $router.push(route)"
        type="button"
		v-bind="$attrs"
		v-on="$listeners"
	>
		<slot></slot>
	</button>
</template>
<script>
export default {
	name: 'Button',
	props: ['route', 'disabled']
};
</script>
