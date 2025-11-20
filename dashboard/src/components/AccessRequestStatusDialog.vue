<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Access Status',
			actions: [
				{
					label: 'Request Another',
					variant: 'subtle',
					iconRight: 'arrow-right',
					onClick: () => {
						open = false;
						emit('openRequestDialog');
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<div
					class="py-3 px-4 font-medium text-green-800 bg-green-50 rounded border border-green-200"
				>
					<p>You have access to this resource via access request.</p>
				</div>
				<div class="space-y-2">
					<p><span class="font-medium">Type:</span> {{ props.doctype }}</p>
					<p><span class="font-medium">Resource:</span> {{ props.docname }}</p>
					<p>
						<span class="font-medium">Expiry:</span>
						{{ dayjs(status.data?.until).fromNow() }}
					</p>
				</div>
				<div class="rounded-sm border divide-y">
					<div class="grid grid-cols-5 font-medium bg-gray-50 divide-x">
						<div class="col-span-2 py-2 px-3">Permission</div>
						<div class="col-span-1 py-2 px-3">Granted</div>
						<div class="col-span-2 py-2 px-3">Expiry</div>
					</div>
					<div
						v-for="permission in status.data?.permissions"
						class="grid grid-cols-5 divide-x"
					>
						<div class="col-span-2 py-2 px-3 font-medium">
							{{ permission.name }}
						</div>
						<div class="col-span-1 py-2 px-3">
							{{ permission.allowed ? 'Yes' : 'No' }}
						</div>
						<div class="col-span-2 py-2 px-3">
							{{ permission.until && dayjs(permission.until).fromNow() }}
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource } from 'frappe-ui';
import { ref } from 'vue';
import dayjs from '../utils/dayjs';

const props = defineProps<{
	doctype: string;
	docname: string;
}>();

const emit = defineEmits<{
	openRequestDialog: [];
}>();

const open = ref(true);

const status = createResource({
	url: 'press.api.access.status',
	auto: true,
	params: {
		doctype: props.doctype,
		docname: props.docname,
	},
});
</script>
