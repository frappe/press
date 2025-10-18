<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Access Request',
			actions,
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<div
					v-if="banner"
					class="py-3 px-4 font-medium rounded border"
					:class="{
						'bg-green-50 border-green-200 text-green-800':
							banner.type === 'success',
						'bg-red-50 border-red-200 text-red-800': banner.type === 'error',
					}"
				>
					{{ banner.message }}
				</div>
				<p v-if="isReceived" class="leading-normal">
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
	status: 'Pending' | 'Accepted' | 'Rejected';
	reason: string;
	siteDomains: boolean;
	loginAsAdministrator: boolean;
	isReceived: boolean;
}>();

const open = ref(true);

const permissions = computed(() =>
	[
		{
			label: 'Login as Administrator',
			requested: props.loginAsAdministrator,
		},
		{
			label: 'Site Domains',
			requested: props.siteDomains,
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

const banner = computed(() => {
	if (props.status === 'Accepted') {
		return {
			type: 'success',
			message: 'This request has been accepted.',
		};
	} else if (props.status === 'Rejected') {
		return {
			type: 'error',
			message: 'This request has been rejected.',
		};
	}
});

const actions = computed(() => {
	if (props.status !== 'Pending' || !props.isReceived) {
		return [];
	}

	return [
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
	];
});
</script>
