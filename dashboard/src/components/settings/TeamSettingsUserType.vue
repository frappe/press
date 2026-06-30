<template>
	<div class="flex items-center gap-2">
		<OwnerIcon v-if="isOwner" class="w-4 h-4 text-yellow-500" />
		<AdminIcon v-else-if="hasAdminAccess" class="w-4 h-4 text-red-500" />
		<div>{{ isOwner ? 'Owner' : hasAdminAccess ? 'Admin' : 'Member' }}</div>
		<Badge v-if="isPending" theme="blue">
			<template #prefix>
				<ClockIcon class="h-3 w-3" />
			</template>
			Invite sent
		</Badge>
	</div>
</template>

<script setup lang="ts">
import { Badge } from 'frappe-ui'
import ClockIcon from '~icons/lucide/clock'
import OwnerIcon from '~icons/lucide/crown'
import AdminIcon from '~icons/lucide/shield-user'

defineProps<{
	hasAdminAccess: boolean
	isOwner: boolean
	isPending: boolean
}>()
</script>
