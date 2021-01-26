<template>
	<a
		v-bind="$attrs"
		v-on="$listeners"
		class="text-blue-500 hover:text-blue-600"
	>
		<slot></slot>
	</a>
</template>
