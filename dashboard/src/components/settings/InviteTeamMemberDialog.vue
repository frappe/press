<template>
	<Dialog
		:options="{
			title: 'Invite User',
			actions: [
				{
					label: 'Invite Member',
					variant: 'solid',
					onClick: inviteMember,
				},
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl label="Email" v-model="email" />
				<Combobox
					v-if="roleOptions[0]?.options?.length > 0"
					v-model="selectedRole"
					label="Role *"
					required
					:options="roleOptions"
					placeholder="Select a role"
					open-on-focus
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Combobox } from 'frappe-ui'
import { toast } from 'vue-sonner'
import router from '../../router'
import { DashboardError } from '../../utils/error'
import { getToastErrorMessage } from '../../utils/toast'

export default {
	components: { Combobox },
	data() {
		return {
			email: '',
			show: true,
			selectedRole: 'Admin',
		}
	},
	resources: {
		roles() {
			return {
				type: 'list',
				doctype: 'Press Role',
				fields: ['name', 'title'],
				initialData: [],
				auto: true,
			}
		},
	},
	computed: {
		roleOptions() {
			let roleItems = [{ label: 'Admin', value: 'Admin' }]
			if (this.$resources.roles.data) {
				for (let role of this.$resources.roles.data) {
					roleItems.push({ label: role.title, value: role.name })
				}
			}
			return [
				{
					group: 'Roles',
					hideLabel: true,
					options: roleItems,
				},
				{
					group: 'Actions',
					hideLabel: true,
					options: [
						{
							type: 'custom',
							key: 'create_role',
							label: 'Create Role',
							condition: () => true,
							onClick: () => {
								router.push({
									name: 'SettingsPermissionRoles',
									query: { createRole: 'true' },
								})
							},
						},
					],
				},
			]
		},
	},
	methods: {
		inviteMember() {
			if (!this.selectedRole) {
				throw new DashboardError('Role is required')
			}
			toast.promise(
				this.$team.inviteTeamMember.submit(
					{
						email: this.email,
						roles: this.selectedRole === 'Admin' ? [] : [this.selectedRole],
					},
					{
						validate: () => {
							if (!this.email) {
								throw new DashboardError('Email is required')
							}
						},
					},
				),
				{
					loading: 'Sending Invite...',
					success: () => {
						this.show = false
						return 'Invite Sent!'
					},
					error: (e) => getToastErrorMessage(e),
				},
			)
		},
	},
}
</script>
