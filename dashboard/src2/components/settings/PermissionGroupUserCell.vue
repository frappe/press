<template>
	<div class="flex">
		<Avatar
			v-for="user in groupUsers.data"
			:image="user.user_image"
			:label="user.full_name"
			class="-ml-1 ring-2 ring-white"
			size="md"
		/>
	</div>
</template>

<script setup>
import { Avatar, createResource } from 'frappe-ui';
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
	transform: data => {
		console.log(data);
		return data.message;
	}
});
</script>
