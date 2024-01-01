<template>
	<div class="flex h-6 items-center">
		<Spinner v-if="groupUsers.loading" class="h-4 w-4 text-gray-500" />
		<AvatarGroup
			v-else-if="groupUsers.data.length > 0"
			:users="groupUsers.data"
		/>
		<div
			v-else-if="groupUsers.data.length == 0"
			class="text-xs text-gray-500"
		>
			No users
		</div>
	</div>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import AvatarGroup from '../AvatarGroup.vue';
const props = defineProps({
	groupId: { type: String, required: true }
});

const groupUsers = createResource({
	url: 'press.api.client.run_doc_method',
	auto: true,
	makeParams() {
		return {
			dt: 'Press Permission Group',
			dn: props.groupId,
			method: 'get_users'
		};
	},
	transform: data => data.message
});
</script>
