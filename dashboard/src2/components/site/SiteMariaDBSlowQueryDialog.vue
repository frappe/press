<template>
	<Dialog
		:options="{
			title: 'Normalized Slow Query',
			size: '2xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<pre
				class="rounded-lg border-2 border-gray-200 bg-gray-100 p-2 p-3 text-sm text-gray-700"
			>
 {{ query }} </pre
			>
			<div class="flex p-2 text-sm">
				<span class="ml-auto pr-2"
					>Duration: {{ duration.toFixed(2) }} seconds</span
				>
				<!-- <span class="pr-2">Rows Examined: {{ rows_examined}}</span>
                <span class="pr-2">Rows Sent: {{rows_sent}}</span>
                <span class="pr-2">Count: {{ count}}</span> -->
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['query', 'duration', 'count', 'rows_examined', 'rows_sent'],
	data() {
		return {
			show: true
		};
	}
};
</script>
