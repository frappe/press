<script setup>
const props = defineProps(['title', 'subtitle']);
</script>

<template>
	<div>
		<div class="flex flex-row items-start justify-between pb-2">
			<div>
				<h1 class="text-2xl font-bold">{{ props.title }}</h1>
				<div class="mt-1 text-base text-gray-600" v-html="props.subtitle"></div>
			</div>
			<div>
				<slot name="actions"> </slot>
			</div>
		</div>
	</div>
</template>
