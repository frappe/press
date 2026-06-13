<template>
	<Dialog
		title="Invite User"
		:actions="[
				{
					label: 'Invite Member',
					variant: 'solid',
					onClick: inviteMember,
				},
			]"
		v-model="show"
	>
		<div class="space-y-4">
			<FormControl label="Email" v-model="email" />
			<FormControl
				v-if="roleOptions.length > 0"
				type="select"
				label="Role *"
				:options="roleOptions"
				v-model="selectedRole"
			/>
		</div>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner'
import { DashboardError } from '../../utils/error'
import { getToastErrorMessage } from '../../utils/toast'

export default {
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
			let options = [{ label: 'Admin', value: 'Admin' }]
			if (this.$resources.roles.data) {
				for (let role of this.$resources.roles.data) {
					options.push({ label: role.title, value: role.name })
				}
			}
			return options
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
