<template>
	<ObjectList :options="listOptions" />
</template>

<script setup lang="jsx">
import { h, ref } from 'vue';
import { toast } from 'vue-sonner';
import { icon, renderDialog, confirmDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import PermissionGroupMembersDialog from './PermissionGroupMembersDialog.vue';
import router from '../../router';
import UserAvatarGroup from '../AvatarGroup.vue';

const listOptions = ref({
	doctype: 'Press Permission Group',
	fields: [{ users: ['user', 'user.full_name', 'user.user_image'] }],
	columns: [
		{
			label: 'Role',
			fieldname: 'title',
			width: 1
		},
		{
			label: 'Members',
			type: 'Component',
			component: ({ row }) => {
				console.log(JSON.stringify(row.users[0].full_name));
				return (
					<div
						onClick={e => {
							e.preventDefault();
							manageMembers(row);
						}}
						class="flex h-6 items-center space-x-2"
					>
						<UserAvatarGroup users={row.users} />
						<Button label="Add Member">
							{{ icon: () => <i-lucide-plus class="h-4 w-4 text-gray-600" /> }}
						</Button>
					</div>
				);
			},
			width: 1
		}
	],
	rowActions({ row, listResource: groupsListResource }) {
		return [
			{
				label: 'Edit Permissions',
				onClick() {
					router.push({
						name: 'SettingsPermissionRolePermissions',
						params: { groupId: row.name }
					});
				}
			},
			{
				label: 'Manage Members',
				onClick: () => manageMembers(row)
			},
			{
				label: 'Delete Group',
				onClick() {
					if (groupsListResource.delete.loading) return;
					confirmDialog({
						title: 'Delete Permission Group',
						message: `Are you sure you want to delete the permission group <b>${row.title}</b>?`,
						onSuccess({ hide }) {
							if (groupsListResource.delete.loading) return;
							toast.promise(groupsListResource.delete.submit(row.name), {
								loading: 'Deleting Group...',
								success: () => {
									`Permission Group ${row.title} Deleted`;
									groupsListResource.reload();
									hide();
								},
								error: e =>
									e.messages.length ? e.messages.join('\n') : e.message
							});
						}
					});
				}
			}
		];
	},
	route(row) {
		return {
			name: 'SettingsPermissionRolePermissions',
			params: { groupId: row.name }
		};
	},
	primaryAction({ listResource: groups }) {
		return {
			label: 'New Role',
			variant: 'solid',
			slots: {
				prefix: icon('plus')
			},
			onClick() {
				confirmDialog({
					title: 'Create Role',
					fields: [
						{
							fieldname: 'title',
							label: 'Role',
							autocomplete: 'off'
						}
					],
					onSuccess({ hide, values }) {
						if (values.title) {
							return groups.insert.submit(
								{ title: values.title },
								{ onSuccess: hide }
							);
						}
						return null;
					}
				});
			}
		};
	}
});

function manageMembers(row) {
	renderDialog(h(PermissionGroupMembersDialog, { groupId: row.name }));
}
</script>
