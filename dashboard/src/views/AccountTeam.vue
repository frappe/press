<template>
	<div>
		<Card
			title="Team"
			subtitle="Teams you are part of and the current active team"
		>
			<ListItem v-for="team in teams" :title="team" :key="team">
				<template #actions>
					<div v-if="$account.team.name === team">
						<Badge color="blue">Active</Badge>
					</div>
					<div v-else class="flex flex-row justify-end">
						<Dropdown class="ml-2" :items="dropdownItems(team)" right>
							<template v-slot="{ toggleDropdown }">
								<Button icon="more-horizontal" @click="toggleDropdown()" />
							</template>
						</Dropdown>
					</div>
				</template>
			</ListItem>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'AccountTeam',
	computed: {
		teams() {
			let current_team = this.$account.team.name;
			if (!this.$account.teams.includes(current_team)) {
				this.$account.teams.push(current_team);
			}
			return this.$account.teams;
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
		}
	},
	methods: {
		dropdownItems(team_name) {
			return [
				{
					label: 'Switch to Team',
					action: () => this.$account.switchToTeam(team_name)
				},
				{
					label: 'Leave Team',
					action: () => this.confirmLeaveTeam(team_name)
				}
			];
		},
		confirmLeaveTeam(team_name) {
			this.$confirm({
				title: 'Leave Team',
				message: `Are you sure you want to leave team <strong>${team_name}</strong>?`,
				actionLabel: 'Leave Team',
				action: closeDialog => {
					closeDialog();
					this.$resources.leaveTeam.submit({ team: team_name });
				}
			});
		}
	}
};
</script>
