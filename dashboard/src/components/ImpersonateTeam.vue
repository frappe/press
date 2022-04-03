<template>
	<div v-if="$account.user">
		<Button
			v-if="$account.user.user_type == 'System User'"
			@click="dialogOpen = true"
		>
			Impersonate Team
		</Button>
		<Dialog v-model="dialogOpen" title="Impersonate Team">
			<Input label="Team" v-model="team" />
			<template v-slot:actions>
				<Button type="primary" @click="$account.switchToTeam(team)">
					Impersonate
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
export default {
	name: 'ImpersonateTeam',
	data() {
		return {
			dialogOpen: false,
			team: null
		};
	}
};
</script>
