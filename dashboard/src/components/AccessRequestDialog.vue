<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Request Access',
			actions: [
				{
					label: 'Cancel',
					variant: 'outline',
					onClick: () => (open = false),
				},
				{
					label: 'Request',
					variant: 'solid',
					onClick: () => request.submit(),
				},
			],
		}"
	>
		<template #body-content>
			<p class="mb-4 text-base">
				Are you sure you want to request access to this resource?
			</p>
			<p class="mb-2 text-base">
				<span class="font-medium">Type:</span> {{ props.doctype }}
			</p>
			<p class="text-base">
				<span class="font-medium">Resource:</span> {{ props.docname }}
			</p>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import { ref } from 'vue';
import { toast } from 'vue-sonner';

const props = defineProps<{
	doctype: string;
	docname: string;
}>();

const open = ref(true);

const request = createResource({
	url: 'press.api.client.insert',
	params: {
		doc: {
			doctype: 'Support Access',
			resources: [
				{
					document_type: props.doctype,
					document_name: props.docname,
				},
			],
		},
	},
	onSuccess: () => {
		open.value = false;
		toast.success('Access request submitted');
	},
	onError: () => toast.error('There was an error submitting your request'),
});
</script>
