<template>
	<LinkControl
		v-if="$attrs.type === 'link'"
		v-bind="$attrs"
		class="min-w-[6rem]"
	/>
	<FormControl v-else v-bind="$attrs" />
</template>
<script setup>
import LinkControl from './LinkControl.vue';
</script>
