<template>
	<div class="space-y-5">
		<div class="ml-auto mr-0 w-max space-x-2">
			<Button
				icon-left="refresh-cw"
				label="Reload"
				variant="subtle"
				@click="() => roles.reload()"
			/>
			<Button
				icon-left="plus"
				variant="solid"
				label="Create Role"
				@click="showCreateDialog = !showCreateDialog"
			/>
		</div>
		<div class="grid grid-cols-3 gap-4 text-base">
			<RouterLink
				v-for="role in roles.data"
				:to="{
					name: 'SettingsPermissionRolePermissions',
					params: {
						id: role.name,
					},
				}"
			>
				<div
					class="px-5 py-4 space-y-3 rounded shadow cursor-pointer hover:shadow-lg transition"
				>
					<div class="font-medium h-6">{{ role.title }}</div>
					<div class="h-6 flex flex-wrap gap-1">
						<div v-for="permission in permissions(role)">
							<Badge
								variant="subtle"
								:theme="permission.color"
								:label="permission.label"
							/>
						</div>
					</div>
					<div class="h-6">
						<div class="flex items-center -space-x-2">
							<Tooltip
								v-for="user in role.users.slice(0, 3)"
								:text="user.full_name"
								:hover-delay="1"
								:placement="'top'"
							>
								<Avatar
									:shape="'circle'"
									:ref_for="true"
									:image="user.user_image"
									:label="user.full_name"
									size="lg"
									class="border border-white"
								/>
							</Tooltip>
							<div
								v-if="role.users.length > 3"
								class="flex items-center justify-center relative shrink-0 w-7 h-7 rounded-full bg-surface-gray-2 border border-white"
							>
								<div class="text-xs font-medium text-ink-gray-5">
									+{{ role.users.length - 3 }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</RouterLink>
		</div>
		<Button
			v-if="roles.hasNextPage"
			icon-left="plus"
			label="Load More"
			@click="() => roles.next()"
		/>
		<RoleCreateDialog
			v-model="showCreateDialog"
			@create="
				(title, users, resources) => {
					insert.submit({
						doc: {
							doctype: 'Press Role',
							title,
							users: users.map((u) => ({
								user: u,
							})),
							resources: resources.map((resource) => ({
								document_type: resource.document_type,
								document_name: resource.document_name,
							})),
						},
					});
				}
			"
		/>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { createListResource, createResource } from 'frappe-ui';
import RoleCreateDialog from './RoleCreateDialog.vue';

const showCreateDialog = ref(false);

const roles = createListResource({
	doctype: 'Press Role',
	fields: [
		'name',
		'title',
		'admin_access',
		'allow_server_creation',
		'allow_site_creation',
		'allow_bench_creation',
		'allow_webhook_configuration',
		{ users: ['user', 'user.full_name', 'user.user_image'] },
	],
	sortBy: 'title',
	sortOrder: 'asc',
	auto: true,
});

const insert = createResource({
	url: 'press.api.client.insert',
	auto: false,
	onSuccess: () => {
		roles.reload();
		showCreateDialog.value = false;
	},
});

const permissions = (role) => {
	return [
		{
			key: 'admin_access',
			label: 'Admin',
			color: 'red',
		},
		{
			key: 'allow_site_creation',
			label: 'Site',
			color: 'green',
		},
		{
			key: 'allow_bench_creation',
			label: 'Bench',
			color: 'green',
		},
		{
			key: 'allow_server_creation',
			label: 'Server',
			color: 'green',
		},
		{
			key: 'allow_webhook_configuration',
			label: 'Webhook',
			color: 'green',
		},
	].filter((permission) => role[permission.key]);
};
</script>
