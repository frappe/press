<template>
	<div
		class="grid border-b"
		:style="{
			gridTemplateColumns: columns.map(col => col.width + 'fr').join(' ')
		}"
	>
		<div
			class="px-2 py-3.5 text-left text-base font-semibold text-gray-900"
			v-for="column in columns"
			:key="column.name"
		>
			{{ column.label }}
		</div>
	</div>
</template>

<script>
export default {
	name: 'TableHeader',
	inject: ['columns']
};
</script>
