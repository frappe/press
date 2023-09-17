<template>
	<component
		:is="row.route ? 'router-link' : 'div'"
		:to="row.route ? row.route : null"
		class="grid"
		:class="{ 'hover:bg-gray-100': row.route }"
		:style="{
			gridTemplateColumns: columns.map(col => col.width + 'fr').join(' ')
		}"
	>
		<slot />
	</component>
</template>

<script>
export default {
	name: 'TableRow',
	props: ['row'],
	inject: ['columns']
};
</script>
