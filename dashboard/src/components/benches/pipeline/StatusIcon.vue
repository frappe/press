<script setup lang="ts">
import { Spinner } from 'frappe-ui'

interface Props {
<<<<<<< HEAD
<<<<<<< HEAD
	status: 'Success' | 'Running' | 'Pending' | 'Queued' | 'Failed' | 'Warning'
=======
	status: 'Success' | 'Running' | 'Pending' | 'Queued' | 'Failed'
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
	status: 'Success' | 'Running' | 'Pending' | 'Queued' | 'Failed' | 'Warning'
>>>>>>> bbd9884f0 (feat(deploy-ui): add warnings/error tab in the sidebar)
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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> bbd9884f0 (feat(deploy-ui): add warnings/error tab in the sidebar)
  <lucide-alert-triangle v-else-if='status == "Warning"'
    class="size-4 shrink-0 text-ink-amber-3" />

	<lucide-circle-x v-else class="size-4 shrink-0 text-ink-red-4" />
<<<<<<< HEAD
=======
	<lucide-circle-x v-else class="size-4 shrink-0 text-ink-red-3" />
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
>>>>>>> bbd9884f0 (feat(deploy-ui): add warnings/error tab in the sidebar)
</template>
