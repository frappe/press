<template>
	<Dialog
		:options="{
			title: 'Normalized Query',
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<pre
				class="mt-2 whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-surface-gray-2 p-3 text-sm text-ink-gray-7"
				>{{ query }}</pre
			>
			<div class="mt-2 flex text-sm">
				<span class="ml-auto">Duration: {{ duration.toFixed(2) }} seconds</span>
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['query', 'duration'],
};
</script>
