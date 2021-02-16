<template>
	<div
		class="flex-col w-full min-h-full md:border-l md:w-2/3"
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
