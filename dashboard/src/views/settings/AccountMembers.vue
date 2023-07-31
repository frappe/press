<template>
	<Card
		title="Team Members"
		subtitle="Team members can access your account on your behalf."
	>
		<template #actions>
			<Button
				v-if="showManageTeamButton"
				@click="showManageMemberDialog = true"
			>
				Add New Member
			</Button>
		</template>
		<div class="max-h-96 divide-y">
			<ListItem
				v-for="member in $account.team_members"
				:title="`${member.first_name} ${member.last_name}`"
				:description="member.name"
				:key="member.name"
			>
				<template #actions>
					<Badge
						v-if="getRoleBadgeProps(member).status == 'Owner'"
						:label="getRoleBadgeProps(member).status"
					/>
					<Button
						v-else
						icon="trash-2"
						@click="removeMember(member)"
						:loading="$resources.removeMember.loading"
					>
					</Button>
				</template>
			</ListItem>
		</div>

		<Dialog
			:options="{
				title: 'Add New Member',
				actions: [
					{
						label: 'Send Invitation',
						variant: 'solid',
						loading: $resources.addMember.loading,
						onClick: () => $resources.addMember.submit({ email: memberEmail })
					}
				]
			}"
			v-model="showManageMemberDialog"
		>
			<template v-slot:body-content>
				<Input
					label="Enter the email address of your teammate to invite them."
					type="text"
					class="mt-2"
					v-model="memberEmail"
					required
				/>
				<ErrorMessage :message="$resourceErrors" />
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountMembers',
	data() {
		return {
			showManageMemberDialog: false,
			showAddMemberForm: false,
			memberEmail: null
		};
	},
	resources: {
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
		removeMember: {
			method: 'press.api.account.remove_team_member',
			onSuccess() {
				this.showManageMemberDialog = false;
				this.$account.fetchAccount();
				this.$notify({
					title: 'Team member removed.',
					icon: 'check',
					color: 'green'
				});
			}
		}
	},
	methods: {
		getRoleBadgeProps(member) {
			let role = 'Member';
			if (this.$account.team.name == member.name) {
				role = 'Owner';
			}

			return {
				status: role,
				color: {
					Owner: 'blue',
					Member: 'gray'
				}[role]
			};
		},
		removeMember(member) {
			this.$confirm({
				title: 'Remove Member',
				message: `Are you sure you want to remove ${member.first_name} ?`,
				actionLabel: 'Remove',
				actionColor: 'red',
				action: closeDialog => {
					this.$resources.removeMember.submit({ user_email: member.name });
					closeDialog();
				}
			});
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
		}
	}
};
</script>
