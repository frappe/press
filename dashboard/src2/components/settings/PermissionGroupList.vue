<template>
	<ObjectList :options="listOptions" />
</template>

<script setup>
import { h, inject, ref } from 'vue';
import { icon, renderDialog, confirmDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import NewPermissionGroupDialog from './NewPermissionGroupDialog.vue';
import PermissionGroupUserCell from './PermissionGroupUserCell.vue';
import PermissionGroupMembersDialog from './PermissionGroupMembersDialog.vue';

const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Permissions', route: '/settings/permissions' },
	{ label: 'Groups', route: '/settings/permissions/groups' }
];

const listOptions = ref({
	resource() {
		return {
			type: 'list',
			doctype: 'Press Permission Group',
			fields: ['title', 'name'],
			auto: true
		};
	},
	columns: [
		{
			label: 'Title',
			fieldname: 'title',
			width: 1
		},
		{
			label: 'Users',
			type: 'Component',
			component: ({ row }) => {
				return h(PermissionGroupUserCell, { groupId: row.name });
			},
			width: 1
		}
	],
	rowActions({ row, listResource: groupsListResource }) {
		return [
			{
				label: 'Manage Group',
				onClick() {
					renderDialog(h(PermissionGroupMembersDialog, { groupId: row.name }));
				}
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
			name: 'PermissionGroupPermissions',
			params: { groupId: row.name }
		};
	},
	primaryAction({ listResource: groups }) {
		return {
			label: 'New Permission Group',
			variant: 'solid',
			slots: {
				prefix: icon('plus')
			},
			onClick() {
				renderDialog(
					h(NewPermissionGroupDialog, {
						onGroupCreated: () => groups.reload()
					})
				);
			}
		};
	}
});
</script>
