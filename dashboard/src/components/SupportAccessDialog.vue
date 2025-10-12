<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Access Request',
			actions: [
				{
					label: 'Reject',
					variant: 'subtle',
					theme: 'red',
					onClick: () => reject.submit(),
				},
				{
					label: 'Accept',
					variant: 'solid',
					onClick: () => accept.submit(),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<p class="leading-normal">
					Do you want to accept or reject this access request from
					<span class="font-medium">{{ requestedBy }}</span>
					for
					<span class="font-medium">{{ resourceType }}</span
					>: <span class="font-medium">{{ resourceName }}</span
					>?
				</p>
				<div v-if="reason" class="space-y-2">
					<p class="font-medium">Reason:</p>
					<p>{{ reason }}</p>
				</div>
				<div v-if="permissions.length" class="space-y-2">
					<p class="font-medium">Permissions:</p>
					<div class="flex flex-wrap gap-2">
						<Badge
							v-for="permission in permissions"
							variant="outline"
							theme="orange"
							size="lg"
						>
							{{ permission.label }}
						</Badge>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Badge, createResource } from 'frappe-ui';
import { computed, ref } from 'vue';

const props = defineProps<{
	name: string;
	requestedBy: string;
	resourceType: string;
	resourceName: string;
	reason: string;
	loginAsAdministrator: boolean;
}>();

const open = ref(true);

const permissions = computed(() =>
	[
		{
			label: 'Login as Administrator',
			requested: props.loginAsAdministrator,
		},
	].filter((p) => p.requested),
);

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
