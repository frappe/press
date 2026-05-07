<template>
	<div class="flex items-center">
		<div class="mr-2 flex items-center">
			<Avatar :image="avatarImage" :label="fullName" size="lg" />
		</div>
		<div>
			<div class="text-sm font-medium text-gray-900">
				{{ fullName }}
			</div>
			<div class="mt-0.5 text-sm text-gray-600">
				{{ email }}
			</div>
		</div>
		<Badge v-if="isCurrentUser" class="ml-2"> You </Badge>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Badge } from 'frappe-ui';

defineProps<{
	avatarImage: string;
	fullName: string;
	email: string;
	isCurrentUser: boolean;
}>();
</script>
