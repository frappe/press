<template>
	<Card
		title="Team"
		subtitle="Teams you are part of and the current active team"
	>
		<template #actions>
			<Button v-if="showManageTeamButton" @click="showManageTeamDialog = true">
				Manage
			</Button>
		</template>
		<ListItem
			v-for="team in teams"
			:title="`${team.team_title}`"
			:description="team.user"
			:key="team"
		>
			<template #actions>
				<div v-if="$account.team.name === team.name">
					<Badge color="blue">Active</Badge>
				</div>
				<div v-else class="flex flex-row justify-end">
					<Dropdown class="ml-2" :options="dropdownItems(team.name)" right>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
				</div>
			</template>
		</ListItem>

		<Dialog :options="{ title: 'Manage Team' }" v-model="showManageTeamDialog">
			<template v-slot:body-content>
				<ListItem
					v-for="member in $account.child_team_members"
					:title="`${member.team_title}`"
					:key="member.name"
				>
					<template #actions>
						<ErrorMessage :message="$resourceErrors" />
						<Button
							class="ml-2 p-4"
							@click="
								$resources.removeMember.submit({ child_team: member.name })
							"
							:loading="$resources.removeMember.loading"
						>
							Remove
						</Button>
					</template>
				</ListItem>
				<div v-if="showManageTeamForm">
					<h5 class="mt-5 text-sm font-semibold">Create child team</h5>
					<Input
						label="Enter name to create a new child team for shared access."
						type="text"
						class="mt-2"
						placeholder="e.g Accounts Team"
						v-model="childTeamTitle"
						required
					/>
					<ErrorMessage :message="$resourceErrors" />

					<div class="mt-5 flex flex-row justify-end">
						<Button @click="showManageTeamForm = false"> Cancel </Button>
						<Button
							class="ml-2"
							appearance="primary"
							:loading="$resources.addChildTeam.loading"
							@click="$resources.addChildTeam.submit({ title: childTeamTitle })"
						>
							Add Child Team
						</Button>
					</div>
				</div>
				<div v-else class="mt-5 flex flex-row justify-end">
					<Button appearance="primary" @click="showManageTeamForm = true">
						Add Child team
					</Button>
				</div>
			</template>
		</Dialog>
	</Card>
</template>

<script>
export default {
	name: 'AccountTeam',
	data() {
		return {
			showManageTeamDialog: false,
			showManageTeamForm: false,
			childTeamTitle: null,
			newChildTeamMessage: 'A new team is created',
			newChildTeamTitle: 'Team Created!'
		};
	},
	computed: {
		teams() {
			return this.$account.teams;
		},
		showManageTeamButton() {
			const team = this.$account.team;
			let show = this.$account.hasRole('Press Admin');
			return show && !this.$account.parent_team;
		}
	},
	resources: {
		leaveTeam() {
			return {
				method: 'press.api.account.leave_team',
				onSuccess() {
					this.$account.fetchAccount();
					this.$notify({
						title: 'Successfully Left Team',
						icon: 'check',
						color: 'green'
					});
				},
				onError() {
					this.$notify({
						title: 'Cannot leave this Team.',
						icon: 'x',
						color: 'red'
					});
				}
			};
		},
		addChildTeam() {
			return {
				method: 'press.api.account.create_child_team',
				onSuccess(data) {
					this.showManageTeamDialog = false;
					this.childTeamTitle = null;
					this.$account.fetchAccount();
					this.$notify({
						title: this.newChildTeamTitle,
						message: this.newChildTeamMessage,
						color: 'green',
						icon: 'check'
					});
				}
			};
		},
		removeMember() {
			return {
				method: 'press.api.account.remove_child_team',
				onSuccess() {
					this.$account.fetchAccount();
				}
			};
		}
	},
	methods: {
		dropdownItems(team_name) {
			return [
				{
					label: 'Switch to Team',
					handler: () => this.$account.switchToTeam(team_name)
				},
				{
					label: 'Leave Team',
					handler: () => this.confirmLeaveTeam(team_name)
				}
			];
		},
		confirmLeaveTeam(team_name) {
			this.$confirm({
				title: 'Leave Team',
				message: `Are you sure you want to leave team <strong>${team_name}</strong>?`,
				actionLabel: 'Leave Team',
				actionType: 'danger',
				action: closeDialog => {
					closeDialog();
					this.$resources.leaveTeam.submit({ team: team_name });
				}
			});
		}
	}
};
</script>
