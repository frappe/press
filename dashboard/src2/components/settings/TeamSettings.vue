<template>
	<div class="p-5">
		<ObjectList :options="teamMembersListOptions"> </ObjectList>
	</div>
</template>

<script setup>
import { h, ref } from 'vue';
import { toast } from 'vue-sonner';
import { getTeam } from '../../data/team';
import { confirmDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import router from '../../router';

const team = getTeam();
team.getTeamMembers.submit();
const teamMembersListOptions = ref({
	onRowClick: () => {},
	rowHeight: 50,
	list: team.getTeamMembers,
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
				label: 'Manage Permissions',
				onClick() {
					router.push({
						name: 'SettingsPermissionRoles'
					});
				}
			},
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
	primaryAction() {
		return {
			label: 'Add Member',
			variant: 'solid',
			iconLeft: 'plus',
			onClick() {
				inviteMemberByEmail();
			}
		};
	}
});

function inviteMemberByEmail() {
	confirmDialog({
		title: 'Add New Member',
		message: 'Enter the email address of your teammate to invite them',
		fields: [
			{
				label: 'Email',
				fieldname: 'email',
				autocomplete: 'off'
			}
		],
		async onSuccess({ hide, values }) {
			if (values.email) {
				return team.inviteTeamMember.submit(
					{ email: values.email, new_dashboard: true },
					{
						onSuccess() {
							hide();
							toast.success('Invite Sent!');
						}
					}
				);
			}
		}
	});
}
</script>
