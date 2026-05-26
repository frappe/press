<script setup lang="ts">
import { Badge, createResource, Select } from 'frappe-ui'
import { h, ref } from 'vue'
import { toast } from 'vue-sonner'
import session from '@/data/session'
import { useUserStore } from '@/stores/user'
import AlertBanner from '../../components/AlertBanner.vue'
import { getTeam } from '../../data/team'
import { confirmDialog } from '../../utils/components'
import dayjs from '../../utils/dayjs'
import { getToastErrorMessage } from '../../utils/toast'
import ObjectList from '../ObjectList.vue'
import UserWithAvatarCell from '../UserWithAvatarCell.vue'
import TeamInviteDialog from './TeamInviteDialog.vue'
import TeamResourcesDialog from './TeamResourcesDialog.vue'

const team = getTeam()
const user = useUserStore()

const isInviteOpen = ref(false)

const members = createResource({
	url: 'run_doc_method',
	auto: true,
	params: {
		method: 'get_members',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
})

const removeUser = createResource({
	url: 'run_doc_method',
	makeParams: (args) => ({
		method: 'remove_user',
		dt: 'Team',
		dn: team.doc.name,
		args,
	}),
	onSuccess: (data) => members.setData(data),
})

const roles = createResource({
	url: 'run_doc_method',
	auto: true,
	params: {
		method: 'get_roles',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
})

const sendInvitation = createResource({
	url: 'run_doc_method',
	makeParams: (args) => ({
		method: 'send_invitation',
		dt: 'Team',
		dn: team.doc.name,
		args,
	}),
	onSuccess: (data) => members.setData(data),
})

const cancelInvitation = createResource({
	url: 'run_doc_method',
	makeParams: (args) => ({
		method: 'cancel_invitation',
		dt: 'Team',
		dn: team.doc.name,
		args,
	}),
	onSuccess: (data) => members.setData(data),
})

const updateTeam = createResource({
	url: 'press.api.client.set_value',
	makeParams: (args) => ({
		doctype: 'Team',
		name: team.doc.name,
		fieldname: args.fieldname,
		value: args.value,
	}),
	onSuccess: () => {
		members.fetch()
	},
})

const updateRole = (member: string, role: string) => {
	updateTeam.submit({
		fieldname: 'team_members',
		value: team.doc.team_members.map((m) => {
			m.role = m.name === member ? role : m.role
			return m
		}),
	})
}

const progress = (promise, msgLoading, msgSuccess) => {
	toast.promise(promise, {
		loading: msgLoading,
		success: msgSuccess,
		error: (e) => getToastErrorMessage(e),
	})
}
</script>

<template>
	<TeamInviteDialog
		v-model="isInviteOpen"
		@success="
			(v) => {
				progress(
					sendInvitation.submit({ names: v }),
					'Sending Invitation...',
					'Invitation Sent',
				);
			}
		"
	/>
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
								isCurrentUser: row.email === user.email,
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
							if (!session.isTeamAdmin) {
								return h(
									Badge,
									{
										label: row.role,
										theme: 'blue',
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
									'onUpdate:modelValue': (value) => updateRole(row.name, value),
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
						label: 'Resources',
						type: 'Component',
						component: ({ row }) => {
							return h(TeamResourcesDialog, {
								team: team.doc.name,
								userId: row.email,
								userName: row.full_name || row.email,
								resourceCount: row.resource_count,
								allServers: row.all_servers,
								allReleaseGroups: row.all_release_groups,
								allSites: row.all_sites,
								onUpdate: (key: string, value: boolean) => {
									updateTeam.submit({
										fieldname: 'team_members',
										value: team.doc.team_members.map((m) => {
											if (m.name === row.name) {
												m[key] = value;
											}
											return m;
										}),
									})
								},
							});
						}
					},
				],
				rowActions: ({ row }) => {
					if (!session.isTeamAdmin) return [];
					if (row.email === user.email) return [];
					return [
						{
							label: 'Resend Invitation',
							icon: 'send',
							condition: () => row.status === 'Pending',
							onClick: () => {
								confirmDialog({
									title: 'Resend invitation',
									message: `Are you sure you want to resend the invitation to <b>${row.email}</b>?`,
									onSuccess: ({ hide }) => {
										progress(
											sendInvitation
												.submit({ names: row.name })
												.then(() => hide()),
											'Sending Invitation...',
											'Invitation Sent',
										);
									},
								});
							},
						},
						{
							label: 'Cancel Invitation',
							icon: 'user-minus',
							condition: () => row.status === 'Pending',
							onClick: () => {
								confirmDialog({
									title: 'Cancel invitation',
									message: `Are you sure you want to cancel the invitation for <b>${row.email}</b>?`,
									onSuccess: ({ hide }) => {
										progress(
											cancelInvitation
												.submit({ account_request: row.name })
												.then(() => hide()),
											'Cancelling Invitation...',
											'Invitation Cancelled',
										);
									},
								});
							},
						},
						{
							label: 'Remove Member',
							icon: 'user-minus',
							condition: () => row.status === 'Active',
							onClick() {
								confirmDialog({
									title: 'Remove member',
									message: `Are you sure you want to remove <b>${row.full_name}</b> from the team?`,
									onSuccess: ({ hide }) => {
										progress(
											removeUser
												.submit({ member: row.name })
												.then(() => hide()),
											'Removing User...',
											'User Removed',
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
							label: 'Invite Users',
							variant: 'subtle',
							iconLeft: 'user-plus',
							onClick: () => (isInviteOpen = true),
						},
					];
				},
			}"
		/>
	</div>
</template>
