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

const roles = createResource({
	url: 'run_doc_method',
	auto: true,
	params: {
		method: 'get_roles',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
});

const sendInvitation = createResource({
	url: 'run_doc_method',
	makeParams: (args) => ({
		method: 'send_invitation',
		dt: 'Team',
		dn: team.doc.name,
		args,
	}),
});

const cancelInvitation = createResource({
	url: 'run_doc_method',
	makeParams: (args) => ({
		method: 'cancel_invitation',
		dt: 'Team',
		dn: team.doc.name,
		args,
	}),
	onSuccess: (data) => members.setData(data),
});

const progress = (promise, msgLoading, msgSuccess) => {
	toast.promise(promise, {
		loading: msgLoading,
		success: msgSuccess,
		error: (e) => getToastErrorMessage(e),
	});
};
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
								fullName: row.full_name || row.email,
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
						type: 'Component',
						component: ({ row }) => {
							if (row.status === 'Pending') {
								return h(
									Badge,
									{
										label: 'Pending',
										theme: 'gray',
										variant: 'subtle',
									},
									row.role,
								);
							}
							return h(
								Select,
								{
									class: 'w-min relative -left-2',
									variant: 'ghost',
									modelValue: row.role,
									options: roles.data,
								},
								row.role,
							);
						},
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Component',
						component: ({ row }) => {
							return h(
								Badge,
								{
									label: row.status,
									theme: row.status === 'Active' ? 'green' : 'gray',
									variant: 'subtle',
								},
								row.status,
							);
						},
					},
					{
						label: 'Joined',
						fieldname: 'date',
						format: (v, r) => {
							if (r.status === 'Pending')
								return 'Expires on ' + dayjs(v).format('LL');
							return dayjs(v).format('LL');
						},
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
							label: 'Send Invitation',
							icon: 'send',
							condition: () => row.status === 'Pending',
							onClick: () =>
								progress(
									sendInvitation.submit({ account_request: row.name }),
									'Sending Invitation...',
									'Invitation Sent',
								),
						},
						{
							label: 'Cancel Invitation',
							icon: 'user-minus',
							condition: () => row.status === 'Pending',
							onClick: () =>
								progress(
									cancelInvitation.submit({ account_request: row.name }),
									'Cancelling Invitation...',
									'Invitation Cancelled',
								),
						},
						{
							label: 'Remove User',
							icon: 'user-minus',
							condition: () => row.status === 'Active',
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
