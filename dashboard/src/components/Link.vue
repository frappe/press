<template>
	<a
		:href="href"
		class="border-b border-gray-800 text-gray-900 outline-gray-400 hover:border-gray-600 hover:text-gray-700"
		><slot
	/></a>
</template>
<script>
export default {
	name: 'Link',
	props: ['href']
};
</script>
