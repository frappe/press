<script setup>
import { defineAsyncComponent, h } from 'vue';
import { Badge, createResource, Select } from 'frappe-ui';
import { toast } from 'vue-sonner';
import dayjs from '../../utils/dayjs';
import { getTeam } from '../../data/team';
import { confirmDialog, renderDialog } from '../../utils/components';
import AlertBanner from '../../components/AlertBanner.vue';
import ObjectList from '../ObjectList.vue';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import { getToastErrorMessage } from '../../utils/toast';

const team = getTeam();

const members = createResource({
	url: 'run_doc_method',
	auto: true,
	params: {
		method: 'get_members',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
});
</script>

<template>
	<div class="p-5">
		<AlertBanner
			title="This page is a work in progress. It is visible to beta testers only."
			class="mb-4"
		/>
		<ObjectList
			:options="{
				rowHeight: 50,
				list: members,
				columns: [
					{
						label: 'User',
						type: 'Component',
						component: ({ row }) => {
							return h(UserWithAvatarCell, {
								avatarImage: row.user_image,
								fullName: row.full_name,
							});
						},
					},
					{
						label: 'Email',
						fieldname: 'email',
					},
					{
						label: 'Role',
						fieldname: 'role',
						width: '120px',
						type: 'Component',
						component: ({ row }) => {
							return h(
								Select,
								{
									class: 'w-min relative -left-2',
									variant: 'ghost',
									modelValue: row.role,
									options: [
										{ label: 'Admin', value: 'Admin' },
										{ label: 'Member', value: 'Member' },
										{ label: 'Developer', value: 'Developer' },
										{ label: 'Viewer', value: 'Viewer' },
									],
								},
								row.role,
							);
						},
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: '120px',
						type: 'Component',
						component: ({ row }) => {
							return h(
								Badge,
								{
									label: row.status,
									theme: row.status === 'Active' ? 'green' : 'gray',
									variant: 'outline',
								},
								row.status,
							);
						},
					},
					{
						label: 'Joined',
						fieldname: 'joined',
						format: (v) => dayjs(v).format('LL'),
					},
					{
						label: 'Resources',
						fieldname: 'joined',
						format: () => '2 Servers, 3 Benches, 5 Sites',
					},
				],
				rowActions({ row }) {
					let team = getTeam();
					if (
						row.name === team.doc.user ||
						row.name === team.doc.user_info?.name
					)
						return [];
					return [
						{
							label: 'Remove User',
							icon: 'user-minus',
							condition: () => row.name !== team.doc.user,
							onClick() {
								if (team.removeTeamMember.loading) return;
								confirmDialog({
									title: 'Remove User',
									message: `Are you sure you want to remove <b>${row.full_name}</b> from this team?`,
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
												error: (e) => getToastErrorMessage(e),
											},
										);
									},
								});
							},
						},
					];
				},
				actions() {
					return [
						{
							label: 'Invite User',
							variant: 'subtle',
							iconLeft: 'user-plus',
							onClick() {
								const InviteTeamMemberDialog = defineAsyncComponent(
									() => import('./InviteTeamMemberDialog.vue'),
								);
								renderDialog(h(InviteTeamMemberDialog));
							},
						},
					];
				},
			}"
		/>
	</div>
</template>
