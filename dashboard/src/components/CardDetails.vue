<template>
	<div
		class="min-h-full w-full flex-col md:w-2/3 md:border-l"
		:class="showDetails ? 'flex' : 'hidden md:flex'"
		:style="{ height: 'calc(100vh - 16rem)' }"
	>
		<slot></slot>
	</div>
</template>
<script>
export default {
	name: 'CardDetails',
	props: ['showDetails']
};
</script>
