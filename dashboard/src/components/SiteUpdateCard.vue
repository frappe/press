<template>
	<button
		class="flex w-full flex-row items-center justify-between rounded-lg border border-gray-100 px-4 py-2 shadow focus:outline-none"
		:class="[
			selected ? 'ring-2 ring-inset ring-blue-500' : '',
			selectable ? 'hover:border-gray-300' : 'cursor-default'
		]"
		ref="card"
	>
		<div class="flex flex-row items-center gap-2">
			<input
				v-if="selectable"
				@click.self="$refs['card'].click()"
				:checked="selected"
				type="checkbox"
				class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-transparent"
			/>
			<h3 class="text-lg font-medium text-gray-900">
				{{ site }}
			</h3>
		</div>
	</button>
</template>

<script>
export default {
	name: 'SiteUpdateCard',
	props: ['site', 'selectable', 'selected'],
};
</script>
