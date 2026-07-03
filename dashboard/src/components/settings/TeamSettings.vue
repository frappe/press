<template>
	<div class="space-y-5 p-5">
		<div
			v-if="showRelaxedPermissions"
			class="rounded bg-surface-amber-2 px-5 py-4"
		>
			<Checkbox
				v-model="relaxedPermissions"
				label="Enable Relaxed Permissions for Members"
			/>
			<p class="ml-[1.375rem] mt-1 text-p-sm text-ink-gray-7">
				When enabled, users with the Member role receive full access by default.
				We recommend disabling this setting so members are granted access only
				through their assigned custom roles.
			</p>
		</div>
		<ObjectList :options="teamMembersListOptions"></ObjectList>
	</div>
</template>

<script setup>
import { Badge, Checkbox, createResource } from 'frappe-ui'
import { computed, defineAsyncComponent, h, ref } from 'vue'
import { toast } from 'vue-sonner'
import ShieldIcon from '~icons/lucide/shield-user'
import session from '../../data/session'
import { getTeam } from '../../data/team'
import router from '../../router'
import { confirmDialog, renderDialog } from '../../utils/components'
import { getToastErrorMessage } from '../../utils/toast'
import ObjectList from '../ObjectList.vue'
import UserWithAvatarCell from '../UserWithAvatarCell.vue'
import TeamSettingsUserType from './TeamSettingsUserType.vue'

const team = getTeam()

const relaxedPermissions = computed({
	get: () => Boolean(team.doc?.relaxed_permissions),
	set: (value) => team.setValue.submit({ relaxed_permissions: value }),
})

// Captured once so unchecking doesn't yank the control away mid-interaction;
// it stays until the next page load.
const showRelaxedPermissions = ref(Boolean(team.doc?.relaxed_permissions))

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
			width: '258px',
			component: ({ row }) => {
				return h(TeamSettingsUserType, {
					hasAdminAccess: row.has_admin_access,
					isOwner: row.user === team.doc.user,
					isPending: row.status === 'Pending',
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
								class: role.name
									? 'cursor-pointer max-w-[124px]'
									: 'max-w-[124px]',
								style: { marginRight: '4px' },
								onClick: role.name
									? (e) => {
											e.preventDefault()
											e.stopPropagation()
											router.push({
												name: 'SettingsPermissionRolePermissions',
												params: { id: role.name },
											})
										}
									: undefined,
							},
							{
								prefix: role.admin_access
									? () => h(ShieldIcon, { class: 'h-3 w-3 text-amber-600' })
									: undefined,
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
		if (row.status === 'Pending') {
			const currentMember = (members.data || []).find(
				(member) => member.user === session.user,
			)
			const canCancelInvitation =
				session.user === team.doc.user || currentMember?.has_admin_access
			if (!canCancelInvitation) return []
			return [
				{
					label: 'Cancel Invitation',
					onClick() {
						if (team.cancelInvitation.loading) return
						confirmDialog({
							title: 'Cancel Invitation',
							message: `Are you sure you want to cancel the invitation sent to <b>${row.email}</b>?`,
							onSuccess({ hide }) {
								if (team.cancelInvitation.loading) return
								toast.promise(
									team.cancelInvitation.submit({ email: row.email }),
									{
										loading: 'Cancelling Invitation...',
										success: () => {
											members.reload()
											hide()
											return 'Invitation Cancelled'
										},
										error: (e) => getToastErrorMessage(e),
									},
								)
							},
						})
					},
				},
			]
		}
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
					renderDialog(
						h(InviteTeamMemberDialog, { onSuccess: () => members.reload() }),
					)
				},
			},
		]
	},
})
</script>
