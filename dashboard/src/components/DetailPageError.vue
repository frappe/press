<template>
	<div v-if="error" class="mx-auto space-y-4 text-center w-fit">
		<p class="text-sm font-medium">
			You do not have permission to view this resource
		</p>
		<Button
			v-if="canRequestAccess"
			variant="solid"
			label="Request Access"
			@click="() => request.submit()"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getTeam } from '../data/team';
import { createResource, toast } from 'frappe-ui';

const props = defineProps<{
	doctype: string;
	docname: string;
	error?: Error;
}>();

const team = getTeam();
const isPermissionError = computed(() => {
	return props.error?.message.endsWith('PermissionError');
});
const canRequestAccess = isPermissionError && team.doc.can_request_access;

const request = createResource({
	url: 'press.api.client.insert',
	auto: false,
	params: {
		doc: {
			doctype: 'Support Access',
			resources: [
				{
					doctype: props.doctype,
					docname: props.docname,
				},
			],
		},
	},
	onSuccess: () => toast.success('Access request submitted'),
	onError: () => toast.error('There was an error submitting your request'),
});
</script>
