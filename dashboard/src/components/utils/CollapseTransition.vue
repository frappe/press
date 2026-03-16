<template>
	<Transition
		name="collapse"
		@enter="(e) => (e.style.height = e.scrollHeight + 'px')"
		@leave="(e) => (e.style.height = '0')"
	>
		<slot />
	</Transition>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
	transition: height 0.3s ease;
	overflow: hidden;
}

.collapse-enter-from {
	height: 0;
}
</style>
