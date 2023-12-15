<template>
	<ObjectList :options="listOptions" />
</template>

<script setup>
import { h, inject, ref } from 'vue';
import { icon, renderDialog } from '../../utils/components';
import NewPermissionGroupDialog from './NewPermissionGroupDialog.vue';
import PermissionGroupUserCell from './PermissionGroupUserCell.vue';

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
				return h(PermissionGroupUserCell, { groupId: row.name })
			},
			width: 1
		}
	],
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
