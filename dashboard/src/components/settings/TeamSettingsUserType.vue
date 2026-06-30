<template>
	<div class="flex items-center gap-2">
		<AdminIcon v-if="hasAdminAccess" class="w-4 h-4 text-red-500" />
		<div>{{ hasAdminAccess ? 'Admin' : 'Member' }}</div>
	</div>
</template>

<script setup lang="ts">
import AdminIcon from '~icons/lucide/shield-user'

defineProps<{
	hasAdminAccess: boolean
}>()
</script>
