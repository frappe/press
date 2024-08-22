<template>
	<div class="flex" v-if="users?.length">
		<Avatar
			v-for="user in users"
			:image="user.user_image"
			:label="user.full_name"
			class="-ml-1 ring-2 ring-white first:ml-0"
			size="lg"
		/>
	</div>
</template>

<script setup>
import { Avatar } from 'frappe-ui';
const props = defineProps({
	users: { type: Array, required: true }
});
</script>
