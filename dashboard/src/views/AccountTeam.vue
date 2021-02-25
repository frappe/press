<template>
	<div>
		<Card
			title="Team"
			subtitle="Teams you are part of and the current active team"
		>
			<div class="divide-y">
				<ListItem v-for="team in teams" :title="team" :key="team">
					<template #actions>
						<div v-if="$account.team.name === team">
							<Badge color="blue">Active</Badge>
						</div>
						<div v-else>
							<Button @click="$account.switchToTeam(team)">
								<span class="text-sm">
									Switch to Team
								</span>
							</Button>
						</div>
					</template>
				</ListItem>
			</div>
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
	}
};
</script>
