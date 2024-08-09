<template>
	<component
		:is="to ? 'router-link' : 'a'"
		v-bind="to ? { to } : { href }"
		class="border-b border-gray-800 text-gray-900 outline-gray-400 hover:border-gray-600 hover:text-gray-700"
	>
		<slot
	/></component>
</template>
<script>
export default {
	name: 'Link',
	props: ['href', 'to']
};
</script>
