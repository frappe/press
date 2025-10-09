<template>
	<Dialog
		:options="{
			title: 'Access Request',
		}"
		v-model="open"
	>
		<template #body-content>
			<p class="text-base leading-normal">
				Do you want to accept or reject access request from
				<span class="font-medium">{{ requestedBy }}</span> for
				<span class="font-medium">{{ resourceType }}</span
				>: <span class="font-medium">{{ resourceName }}</span
				>?
			</p>
		</template>
		<template #actions>
			<div class="flex flex-row-reverse gap-2 justify-start">
				<Button variant="solid" @click="() => accept.submit()"> Accept </Button>
				<Button variant="subtle" theme="red" @click="() => reject.submit()">
					Reject
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import { ref } from 'vue';

const props = defineProps<{
	name: string;
	requestedBy: string;
	resourceType: string;
	resourceName: string;
}>();

const open = ref(true);

const accept = createResource({
	url: 'press.api.client.set_value',
	params: {
		doctype: 'Support Access',
		name: props.name,
		fieldname: 'status',
		value: 'Accepted',
	},
	onSuccess: () => {
		open.value = false;
	},
});

const reject = createResource({
	url: 'press.api.client.set_value',
	params: {
		doctype: 'Support Access',
		name: props.name,
		fieldname: 'status',
		value: 'Rejected',
	},
	onSuccess: () => {
		open.value = false;
	},
});
</script>
