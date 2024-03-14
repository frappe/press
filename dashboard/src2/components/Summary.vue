<template>
	<div class="w-full">
		<h2 class="text-base font-medium leading-6 text-gray-900">Summary</h2>
		<div
			class="mt-2 grid gap-x-4 gap-y-2 rounded-md border bg-gray-50 p-4 text-p-base"
			style="grid-template-columns: 4fr 4fr"
		>
			<template v-for="option in options" :key="option.label">
				<div
					v-if="option.condition ? option.condition() : true"
					class="text-gray-600"
				>
					{{ option.label }}:
				</div>
				<div
					v-if="option.condition ? option.condition() : true"
					class="text-gray-900"
					v-html="option.value"
				/>
			</template>
		</div>
	</div>
</template>

<script>
export default {
	props: ['options']
};
</script>
