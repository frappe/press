<template>
	<LinkControl
		v-if="$attrs.type === 'link'"
		v-bind="$attrs"
		class="min-w-[6rem]"
	/>
	<TabButtons v-else-if="$attrs.type === 'tab'" v-bind="$attrs" />
	<FormControl v-else v-bind="$attrs" />
</template>
<script setup>
import { TabButtons } from 'frappe-ui';
import LinkControl from './LinkControl.vue';
</script>
