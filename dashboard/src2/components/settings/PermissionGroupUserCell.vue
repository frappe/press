<template>
	<div class="h-6 flex items-center">
		<AvatarGroup v-if="groupUsers.data" :users="groupUsers.data" />
		<Spinner v-else-if="groupUsers.loading" class="h-4 w-4 text-gray-500" />
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
