<script setup lang="ts">
import { RadioGroupItem, RadioGroupRoot } from 'reka-ui';

interface Item {
	value: string;
	disabled?: boolean;
	[key: string]: any;
}

interface Props {
	items: Item[];
	itemClass?: string;
}

defineProps<Props>();
</script>

<template>
	<RadioGroupRoot>
		<RadioGroupItem
			v-for="item in items"
			:key="item.value"
			class="border data-[state=checked]:border-outline-gray-5 hover:bg-surface-gray-1 disabled:opacity-50 disabled:cursor-not-allowed rounded"
			:class="itemClass"
			:value="item.value"
			:disabled="item.disabled"
		>
			<slot name="item" v-bind="{ item }" />
		</RadioGroupItem>
		<slot />
	</RadioGroupRoot>
</template>
