<template>
	<div class="flex items-center">
		<div class="mr-2 flex items-center">
			<Avatar :image="avatarImage" :label="fullName" size="lg" />
		</div>
		<div>
			<div class="text-sm font-medium text-gray-900">
				{{ fullName }}
			</div>
			<div class="text-sm text-gray-500">
				{{ email }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { Avatar } from 'frappe-ui';
const props = defineProps({
	avatarImage: String,
	fullName: String,
	email: String
});
</script>