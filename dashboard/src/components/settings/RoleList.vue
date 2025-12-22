<template>
<<<<<<< HEAD
	<ObjectList :options="listOptions" />
=======
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
								v-if="role.users.length > 4"
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
>>>>>>> b416a6038 (fix(dashboard): Roles list members count style)
</template>

<script setup lang="jsx">
import { h, ref } from 'vue';
import { toast } from 'vue-sonner';
import { FeatherIcon } from 'frappe-ui';
import { icon, renderDialog, confirmDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import RoleConfigureDialog from './RoleConfigureDialog.vue';
import router from '../../router';
import UserAvatarGroup from '../AvatarGroup.vue';
import { getToastErrorMessage } from '../../utils/toast';

const listOptions = ref({
	doctype: 'Press Role',
	fields: [
		{ users: ['user', 'user.full_name', 'user.user_image'] },
		'admin_access',
	],
<<<<<<< HEAD
	documentation: 'https://docs.frappe.io/cloud/role-permissions',
	columns: [
		{
			label: 'Role',
			fieldname: 'title',
			width: 1,
			suffix: (row) => {
				return row.admin_access ? (
					<FeatherIcon name="shield" class="ml-1 h-4 w-4 text-gray-700" />
				) : null;
			},
		},
		{
			label: 'Members',
			type: 'Component',
			component: ({ row }) => {
				return (
					<div
						onClick={(e) => {
							e.preventDefault();
							configureRole(row);
						}}
						class="flex h-6 items-center space-x-2"
					>
						<UserAvatarGroup users={row.users} />
						<Button label="Add Member">
							{{ icon: () => <lucide-plus class="h-4 w-4 text-gray-600" /> }}
						</Button>
					</div>
				);
			},
			width: 1,
		},
	],
	rowActions({ row, listResource: roleListResource }) {
		return [
			{
				label: 'Edit Permissions',
				onClick() {
					router.push({
						name: 'SettingsPermissionRolePermissions',
						params: { roleId: row.name },
					});
				},
			},
			{
				label: 'Configure Role',
				onClick: () => configureRole(row),
			},
			{
				label: 'Delete Role',
				onClick() {
					if (roleListResource.delete.loading) return;
					confirmDialog({
						title: 'Delete Role',
						message: `Are you sure you want to delete the role <b>${row.title}</b>?`,
						onSuccess({ hide }) {
							if (roleListResource.delete.loading) return;
							toast.promise(roleListResource.delete.submit(row.name), {
								loading: 'Deleting Role...',
								success: () => {
									roleListResource.reload();
									hide();
									return `Role ${row.title} deleted`;
								},
								error: (e) => getToastErrorMessage(e),
							});
						},
					});
				},
			},
		];
	},
	route(row) {
		return {
			name: 'SettingsPermissionRolePermissions',
			params: { roleId: row.name },
		};
	},
	primaryAction({ listResource: groups }) {
		return {
			label: 'New Role',
			variant: 'solid',
			slots: {
				prefix: icon('plus'),
			},
			onClick() {
				confirmDialog({
					title: 'Create Role',
					fields: [
						{
							fieldname: 'title',
							label: 'Role',
							autocomplete: 'off',
						},
					],
					onSuccess({ hide, values }) {
						if (values.title) {
							return groups.insert.submit(
								{ title: values.title },
								{ onSuccess: hide },
							);
						}
						return null;
					},
				});
			},
		};
=======
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
>>>>>>> a8f659426 (fix(dashboard): Create role dialog not opening)
	},
});

function configureRole(row) {
	renderDialog(h(RoleConfigureDialog, { roleId: row.name }));
}
</script>
