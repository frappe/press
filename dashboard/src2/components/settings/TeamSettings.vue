<template>
	<div class="p-5">
		<ObjectList :options="teamMembersListOptions"> </ObjectList>
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
		data: computed(() => team.getTeamMembers.data || []),
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
	},
	primaryAction({ listResource }) {
		return {
			label: 'Add Member',
			variant: 'solid',
			iconLeft: 'plus',
			onClick() {
				handleNewMemberClick(listResource);
			}
		};
	}
});

function handleNewMemberClick(membersListResource) {
	renderDialog(
		h(AddTeamMemberDialog, {
			onMemberAdded: () => membersListResource.reload()
		})
	);
}
</script>
