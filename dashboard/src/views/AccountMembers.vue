<template>
	<Card
		title="Team Members"
		subtitle="Team members can access your account on your behalf."
	>
		<template #actions>
			<Button
				v-if="
					$account.hasRole('Press Admin') &&
						($account.team.default_payment_method ||
							$account.team.payment_mode == 'Prepaid Credits' ||
							$account.team.free_account ||
							$account.team.erpnext_partner)
				"
				@click="showAddMemberDialog = true"
			>
				Add Member
			</Button>
		</template>
		<div class="divide-y">
			<ListItem
				v-for="member in $account.team_members"
				:title="`${member.first_name} ${member.last_name}`"
				:description="member.name"
				:key="member.name"
			>
				<template #actions>
					<Badge v-bind="getRoleBadgeProps(member)" />
				</template>
			</ListItem>
		</div>

		<Dialog title="Add Member" v-model="showAddMemberDialog">
			<Input
				label="Enter the email address of your teammate to invite them."
				type="text"
				class="mt-4"
				v-model="memberEmail"
				required
			/>
			<ErrorMessage :error="addMember.error" />

			<div slot="actions">
				<Button @click="showAddMemberDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-2"
					type="primary"
					:loading="addMember.loading"
					@click="addMember.submit({ email: memberEmail })"
				>
					Send Invitation
				</Button>
			</div>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'AccountMembers',
	data() {
		return {
			showAddMemberDialog: false,
			memberEmail: null
		};
	},
	resources: {
		addMember: {
			method: 'press.api.account.add_team_member',
			onSuccess() {
				this.showAddMemberDialog = false;
				this.memberEmail = null;
				this.$notify({
					title: 'Invite Sent!',
					message: 'They will receive an email shortly to join your team.',
					color: 'green',
					icon: 'check'
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
		}
	}
};
</script>
