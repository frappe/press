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
						'bg-gray-50 border-gray-200 text-gray-800':
							banner.type === 'neutral',
					}"
				>
					{{ banner.message }}
				</div>
				<p v-if="isReceived && isPending" class="leading-normal">
					Do you want to accept or reject this access request?
				</p>
				<div class="rounded-sm border divide-y">
					<div
						v-for="resource in request.doc?.resources"
						class="grid grid-cols-3 divide-x"
					>
						<div class="col-span-1 py-2 px-3 font-medium">
							{{ resource.document_type }}
						</div>
						<div class="col-span-2 py-2 px-3">
							<Link
								:to="
									resourceLink(resource.document_type, resource.document_name)
								"
								@click="
									() =>
										resourceLink(
											resource.document_type,
											resource.document_name,
										) && (open = false)
								"
							>
								{{ resource.document_name }}
							</Link>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<div>Valid For</div>
					<div>
						<Select
							v-model="request.doc.allowed_for"
							:options="validityOptions"
							:disabled="!isPending"
						/>
					</div>
				</div>
				<div v-if="request.doc?.reason" class="space-y-2">
					<p class="font-medium">Reason:</p>
					<p class="leading-relaxed">{{ request.doc?.reason }}</p>
				</div>
				<div v-if="permissions.length" class="space-y-2">
					<p class="font-medium">Permissions:</p>
					<div class="flex flex-wrap gap-2">
						<Badge
							v-for="permission in permissions"
							variant="outline"
							:theme="permission.color"
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
import Link from './Link.vue';
import {
	Badge,
	Select,
	createResource,
	createDocumentResource,
} from 'frappe-ui';
import { computed, ref, watch } from 'vue';
import { getTeam } from '../data/team';
import { toast } from 'vue-sonner';

const props = defineProps<{
	name: string;
}>();

const open = ref(true);
const team = getTeam();

const request = createDocumentResource({
	doctype: 'Support Access',
	name: props.name,
	auto: true,
});

const isReceived = computed(() => {
	return team.doc?.name === request.doc?.target_team;
});

const isPending = computed(() => {
	return request.doc?.status === 'Pending';
});

const validityOptions = [
	{ label: '3 Hours', value: '3' },
	{ label: '6 Hours', value: '6' },
	{ label: '12 Hours', value: '12' },
	{ label: '1 Day', value: '24' },
	{ label: '3 Days', value: '72' },
	{ label: '7 Days', value: '168' },
];

const permissions = computed(() =>
	[
		{
			label: 'Release Group',
			requested: request.doc?.site_release_group,
			color: 'red',
		},
		{
			label: 'SSH',
			requested: request.doc?.bench_ssh,
			color: 'red',
		},
		{
			label: 'Login as Administrator',
			requested: request.doc?.login_as_administrator,
			color: 'orange',
		},
		{
			label: 'Domains',
			requested: request.doc?.site_domains,
			color: 'green',
		},
	].filter((p) => p.requested),
);

const update = createResource({
	url: 'press.api.client.set_value',
	makeParams: (args: any) => ({
		doctype: 'Support Access',
		name: props.name,
		fieldname: {
			status: args.status,
			allowed_for: args.allowed_for,
		},
	}),
	onSuccess: (data: any) => {
		toast.success(`Request ${data.status}`);
		open.value = false;
	},
});

const banner = computed(() => {
	if (request.doc?.status === 'Accepted') {
		return {
			type: 'success',
			message: 'This request has been accepted.',
		};
	} else if (request.doc?.status === 'Rejected') {
		return {
			type: 'error',
			message: 'This request has been rejected.',
		};
	} else if (request.doc?.status === 'Revoked') {
		return {
			type: 'neutral',
			message: 'This request has been revoked.',
		};
	} else if (request.doc?.status === 'Forfeited') {
		return {
			type: 'neutral',
			message: 'This request has been forfeited.',
		};
	}
});

const actions = computed(() => {
	const actions = [];
	const isExpired = new Date(request.doc.access_allowed_till) < new Date();

	if (request.doc?.status === 'Pending' && isReceived.value) {
		actions.push(
			{
				label: 'Reject',
				variant: 'subtle',
				theme: 'red',
				onClick: () => {
					update.submit({
						status: 'Rejected',
						allowed_for: request.doc.allowed_for,
					});
				},
			},
			{
				label: 'Accept',
				variant: 'solid',
				onClick: () => {
					update.submit({
						status: 'Accepted',
						allowed_for: request.doc.allowed_for,
					});
				},
			},
		);
	}

	if (request.doc?.status === 'Accepted' && isReceived.value && !isExpired) {
		actions.push({
			label: 'Revoke',
			variant: 'subtle',
			theme: 'red',
			onClick: () => {
				update.submit({
					status: 'Revoked',
					allowed_for: request.doc.allowed_for,
				});
			},
		});
	}

	if (request.doc?.status === 'Accepted' && !isReceived.value && !isExpired) {
		actions.push({
			label: 'Forfeit',
			variant: 'subtle',
			theme: 'red',
			onClick: () => {
				update.submit({
					status: 'Forfeited',
					allowed_for: request.doc.allowed_for,
				});
			},
		});
	}

	return actions;
});

const resourceLink = (documentType: string, documentName: string) => {
	switch (documentType) {
		case 'Site':
			return {
				name: 'Site Detail',
				params: {
					name: documentName,
				},
			};
		case 'Release Group':
			return {
				name: 'Release Group Detail',
				params: {
					name: documentName,
				},
			};
		case 'Bench':
			return {
				name: 'Bench Detail',
				params: {
					name: documentName,
				},
			};
	}
};
</script>
