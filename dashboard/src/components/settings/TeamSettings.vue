<template>
	<div class="p-5">
		<ObjectList :options="teamMembersListOptions"></ObjectList>
	</div>
</template>

<script setup>
import { Badge, createResource } from 'frappe-ui'
import { defineAsyncComponent, h, ref } from 'vue'
import { toast } from 'vue-sonner'
import session from '../../data/session'
import { getTeam } from '../../data/team'
import router from '../../router'
import { confirmDialog, renderDialog } from '../../utils/components'
import { getToastErrorMessage } from '../../utils/toast'
import ObjectList from '../ObjectList.vue'
import UserWithAvatarCell from '../UserWithAvatarCell.vue'
import TeamSettingsUserType from './TeamSettingsUserType.vue'

const team = getTeam()

const members = createResource({
	url: 'press.api.client.run_doc_method',
	auto: true,
	params: {
		method: 'members',
		dt: 'Team',
		dn: team.doc.name,
	},
	transform: (d) => d.message,
})

const teamMembersListOptions = ref({
	onRowClick: () => {},
	rowHeight: 50,
	list: members,
	columns: [
		{
			label: 'User',
			type: 'Component',
			width: '300px',
			component: ({ row }) => {
				return h(UserWithAvatarCell, {
					avatarImage: row.user_image,
					fullName: row.user_name,
					email: row.email,
					isCurrentUser: row.user === session.user,
				})
			},
		},
		{
			label: 'User type',
			type: 'Component',
			width: '100px',
			component: ({ row }) => {
				return h(TeamSettingsUserType, {
					hasAdminAccess: row.has_admin_access,
					isOwner: row.user === team.doc.user,
				})
			},
		},
		{
			label: 'Role',
			type: 'Component',
			component: ({ row }) => {
				let roles = row.roles || []
				return h(
					'div',
					{ class: 'flex flex-wrap gap-1.5' },
					roles.map((role) =>
						h(
							Badge,
							{
								key: role.name,
								variant: 'subtle',
								class: 'cursor-pointer max-w-[124px]',
								style: { marginRight: '4px' },
								onClick: (e) => {
									e.preventDefault()
									e.stopPropagation()
									router.push({
										name: 'SettingsPermissionRolePermissions',
										params: { id: role.name },
									})
								},
							},
							{
								default: () =>
									h('span', { class: 'truncate min-w-0' }, role.title),
							},
						),
					),
				)
			},
		},
	],
	rowActions({ row }) {
		let team = getTeam()
		if (row.user === team.doc.user || row.user === team.doc.user_info?.name)
			return []
		return [
			{
				label: 'Remove Member',
				condition: () => row.user !== team.doc.user,
				onClick() {
					if (team.removeTeamMember.loading) return
					confirmDialog({
						title: 'Remove Member',
						message: `Are you sure you want to remove <b>${row.user_name}</b> from the team?`,
						onSuccess({ hide }) {
							if (team.removeTeamMember.loading) return
							toast.promise(
								team.removeTeamMember.submit({ member: row.user }),
								{
									loading: 'Removing Member...',
									success: () => {
										members.reload()
										hide()
										return 'Member Removed'
									},
									error: (e) => getToastErrorMessage(e),
								},
							)
						},
					})
				},
			},
		]
	},
	actions() {
		return [
			{
				label: 'Settings',
				iconLeft: 'settings',
				onClick() {
					const TeamSettingsDialog = defineAsyncComponent(
						() => import('./TeamSettingsDialog.vue'),
					)
					renderDialog(h(TeamSettingsDialog))
				},
			},
			{
				label: 'Invite User',
				variant: 'solid',
				iconLeft: 'user-plus',
				onClick() {
					const InviteTeamMemberDialog = defineAsyncComponent(
						() => import('./InviteTeamMemberDialog.vue'),
					)
					renderDialog(h(InviteTeamMemberDialog))
				},
			},
		]
	},
})
</script>
