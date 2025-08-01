<template>
	<ObjectList :options="listOptions" />
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
	},
});

function configureRole(row) {
	renderDialog(h(RoleConfigureDialog, { roleId: row.name }));
}
</script>
