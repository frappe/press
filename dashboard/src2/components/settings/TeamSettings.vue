<template>
	<div class="grid grid-cols-1 items-start gap-5 p-4 sm:grid-cols-2">
		<div class="rounded-md border p-4">
			<ObjectList :options="teamMembersListOptions">
				<template #header-left>
					<div class="flex items-center">
						<h2 class="pl-1 text-lg font-medium text-gray-900">Members</h2>
					</div>
				</template>
				<template #header-right="{ listResource: membersListResource }">
					<Button
						iconLeft="plus"
						@click="() => handleNewMemberClick(membersListResource)"
					>
						Add Member
					</Button>
				</template>
			</ObjectList>
		</div>
		<div class="rounded-md border p-4">
			<ObjectList :options="permissionGroupsListOptions">
				<template #header-left>
					<div class="flex items-center">
						<h2 class="pl-1 text-lg font-medium text-gray-900">Groups</h2>
					</div>
				</template>
				<template #header-right="{ listResource: groupsListResource }">
					<Button
						iconLeft="plus"
						@click="() => handleNewGroupClick(groupsListResource)"
					>
						Add Group
					</Button>
				</template>
			</ObjectList>
		</div>
	</div>
</template>

<script setup>
import { computed, h, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { getTeam } from '../../data/team';
import { confirmDialog, renderDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import AddTeamMemberDialog from './AddTeamMemberDialog.vue';
import NewPermissionGroupDialog from './NewPermissionGroupDialog.vue';
import PermissionGroupUserCell from './PermissionGroupUserCell.vue';

const breadcrumbs = inject('breadcrumbs');
breadcrumbs.value = [
	{ label: 'Settings', route: '/settings' },
	{ label: 'Team', route: '/settings/team' }
];

const team = getTeam();
team.getTeamMembers.submit();
const teamMembersListOptions = ref({
	list: {
		data: computed(() => team.getTeamMembers.data?.message || []),
		reload: () => team.getTeamMembers.submit(),
		loading: computed(() => team.getTeamMembers.loading)
	},
	columns: [
		{
			label: 'User',
			type: 'Component',
			component: ({ row }) => {
				return h(UserWithAvatarCell, {
					avatarImage: row.user_image,
					fullName: row.full_name,
					email: row.email
				});
			},
			width: 1
		}
	],
	rowActions({ row }) {
		let team = getTeam();
		if (row.name === team.doc.user) return [];
		return [
			{
				label: 'Remove Member',
				condition: () => row.name !== team.doc.user,
				onClick() {
					if (team.removeTeamMember.loading) return;
					confirmDialog({
						title: 'Remove Member',
						message: `Are you sure you want to remove <b>${row.full_name}</b> from the team?`,
						onSuccess({ hide }) {
							if (team.removeTeamMember.loading) return;
							toast.promise(
								team.removeTeamMember.submit({ member: row.name }),
								{
									loading: 'Removing Member...',
									success: () => {
										team.getTeamMembers.submit();
										hide();
										return 'Member Removed';
									},
									error: e =>
										e.messages.length ? e.messages.join('\n') : e.message
								}
							);
						}
					});
				}
			}
		];
	}
});

function handleNewMemberClick(membersListResource) {
	renderDialog(
		h(AddTeamMemberDialog, {
			onMemberAdded: () => membersListResource.reload()
		})
	);
}

const permissionGroupsListOptions = ref({
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
	}
});
function handleNewGroupClick(groupsListResource) {
	renderDialog(
		h(NewPermissionGroupDialog, {
			onGroupCreated: () => groupsListResource.reload()
		})
	);
}
</script>
