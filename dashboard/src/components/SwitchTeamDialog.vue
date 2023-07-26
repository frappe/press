<template>
	<Dialog :options="{ title: 'Switch Team' }">
		<template v-slot:body-content>
			<span class="text-xs text-gray-600"
				>Current Team: {{ $account.team.name }}</span
			>
			<div class="border-t my-2">
				<ListItem
					v-for="team in $account.teams"
					:title="`${team.team_title}`"
					:description="team.user"
					:key="team"
				>
					<template #actions>
						<div v-if="$account.team.name === team.name">
							<Badge theme="blue">Active</Badge>
						</div>
						<div v-else class="flex flex-row justify-end">
							<Button @click="$account.switchToTeam(team.name)">
								Switch
							</Button>
						</div>
					</template>
				</ListItem>
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'SwitchTeamDialog'
};
</script>
