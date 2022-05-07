<script setup>
import { computed } from 'vue';
const props = defineProps({ app:Object });

const title = computed(() => {
	return props.app.title;
})
</script>

<template>
	<div>
		{{ title }}
	</div>
</template>

