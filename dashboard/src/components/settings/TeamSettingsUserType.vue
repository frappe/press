<template>
	<div class="flex items-center gap-2">
		<OwnerIcon v-if="isOwner" class="w-4 h-4 text-yellow-500" />
		<AdminIcon v-else-if="hasAdminAccess" class="w-4 h-4 text-red-500" />
		<div>{{ isOwner ? 'Owner' : hasAdminAccess ? 'Admin' : 'Member' }}</div>
	</div>
</template>

<script setup lang="ts">
import OwnerIcon from '~icons/lucide/crown'
import AdminIcon from '~icons/lucide/shield-user'

defineProps<{
	hasAdminAccess: boolean
	isOwner: boolean
}>()
</script>
