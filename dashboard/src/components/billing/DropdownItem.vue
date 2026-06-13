<template>
	<div>
		<Button
			class="flex w-full justify-between rounded text-base"
			variant="ghost"
			:label="label"
			@click="onClick"
		>
			<template v-if="active" #suffix>
				<span class="lucide-check h-4" />
			</template>
			<slot />
		</Button>
	</div>
</template>
<script setup>
import { Button } from 'frappe-ui'
const props = defineProps({
	label: String,
	active: Boolean,
	onClick: Array,
})
</script>
