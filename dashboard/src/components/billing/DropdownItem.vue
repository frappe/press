<template>
	<div>
		<Button
			class="flex w-full justify-between rounded text-base"
			variant="ghost"
			:label="label"
			@click="onClick"
		>
			<template v-if="active" #suffix>
				<FeatherIcon class="h-4" name="check" />
			</template>
			<slot />
		</Button>
	</div>
</template>
<script setup>
import { Button, FeatherIcon } from 'frappe-ui';
const props = defineProps({
	label: String,
	active: Boolean,
	onClick: Array,
});
</script>
