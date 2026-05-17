<script setup lang="ts">
import { Spinner } from 'frappe-ui'

interface Props {
	status: 'Success' | 'Running' | 'Pending' | 'Queued' | 'Failed'
}

defineProps<Props>()
</script>

<template>
	<lucide-circle-check
		v-if='status == "Success"'
		class="size-4 text-ink-green-3 shrink-0"
	/>

	<Spinner v-else-if='status== "Running"' class="size-4 shrink-0" />

	<lucide-circle-dot-dashed
		v-else-if='["Pending","Queued"].includes(status)'
		class="size-4 shrink-0 text-ink-gray-5"
	/>

	<lucide-circle-x v-else class="size-4 shrink-0 text-ink-red-3" />
</template>
