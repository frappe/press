<template>
	<Card
		title="Group Permissions"
		subtitle="Create a group or permission and assign it to your team members"
	>
		<template #actions>
			<Button v-if="showManageTeamButton" @click="showAddGroupDialog = true">
				Add New Group
			</Button>
		</template>
		<div class="max-h-96 divide-y">
			<ListItem
				v-for="group in groups"
				:title="group.title"
				:description="group.name"
				:key="group.name"
			>
				<template #actions>
					<Dropdown :options="dropdownItems(group)" right>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
				</template>
			</ListItem>
		</div>
	</Card>

	<EditPermissions
		:type="'group'"
		:show="showEditMemberDialog"
		:name="group.name"
		@close="showEditMemberDialog = false"
	/>

	<ManageGroupMembers
		v-model:group="group"
		:show="showGroupMemberDialog"
		@close="showGroupMemberDialog = false"
	/>

	<Dialog
		:options="{
			title: 'Add New Group',
			actions: [
				{
					label: 'Create Group',
					variant: 'solid',
					loading: $resources.addGroup.loading,
					onClick: () => $resources.addGroup.submit({ title: groupName })
				}
			]
		}"
		v-model="showAddGroupDialog"
	>
		<template v-slot:body-content>
			<Input :label="'Title'" type="text" v-model="groupName" required />
		</template>
	</Dialog>
</template>
<script>
import EditPermissions from './EditPermissions.vue';
import ManageGroupMembers from './ManageGroupMembers.vue';

export default {
	name: 'AccountGroups',
	components: {
		EditPermissions,
		ManageGroupMembers
	},
	data() {
		return {
			groupName: '',
			memberEmail: '',
			showAddGroupDialog: false,
			showGroupMemberDialog: false,
			showManageMemberDialog: false,
			showEditMemberDialog: false,
			group: { name: '', title: '' },
			showAddMemberForm: false
		};
	},
	resources: {
		groups: {
			method: 'press.api.account.groups',
			auto: true
		},
		addMember: {
			method: 'press.api.account.add_team_member',
			onSuccess() {
				this.showManageMemberDialog = false;
				this.memberEmail = null;
				this.$notify({
					title: 'Invite Sent!',
					message: 'They will receive an email shortly to join your team.',
					color: 'green',
					icon: 'check'
				});
			}
		},
		addGroup: {
			method: 'press.api.account.add_permission_group',
			validate() {
				if (this.groupName.length == 0) {
					return 'Group name is required.';
				}
			},
			onSuccess(r) {
				this.$resources.groups.fetch();
				this.$notify({
					title: 'Group Created!',
					message: 'You can now assign this group to your team members',
					color: 'green',
					icon: 'check'
				});
				this.showAddGroupDialog = false;
			}
		},
		removeGroup: {
			method: 'press.api.account.remove_permission_group',
			onSuccess() {
				this.$resources.groups.fetch();
				this.$notify({
					title: 'Group Removed!',
					message: 'Permissions have been removed from all team members',
					color: 'green',
					icon: 'check'
				});
			}
		}
	},
	methods: {
		removeGroup(group) {
			this.$confirm({
				title: 'Remove Group',
				message: `Are you sure you want to remove ${group.title} ?`,
				actionLabel: 'Remove',
				actionColor: 'red',
				action: closeDialog => {
					this.$resources.removeGroup.submit({ name: group.name });
					closeDialog();
				}
			});
		},
		dropdownItems(group) {
			return [
				{
					label: 'Manage Members',
					icon: 'users',
					onClick: () => {
						this.group = group;
						this.showGroupMemberDialog = true;
					}
				},
				{
					label: 'Edit Permissions',
					icon: 'edit',
					onClick: () => {
						this.group = group;
						this.showEditMemberDialog = true;
					}
				},
				{
					label: 'Remove',
					icon: 'trash-2',
					onClick: () => this.removeGroup(group)
				}
			];
		}
	},
	computed: {
		showManageTeamButton() {
			const team = this.$account.team;
			let show = this.$account.hasRole('Press Admin');
			return (
				show &&
				(team.default_payment_method ||
					team.payment_mode == 'Prepaid Credits' ||
					team.free_account ||
					team.erpnext_partner ||
					team.parent_team)
			);
		},
		groups() {
			if (!this.$resources.groups.data) return [];
			return this.$resources.groups.data;
		}
	}
};
</script>
