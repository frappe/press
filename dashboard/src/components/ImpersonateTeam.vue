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
			<Button
				slot="actions"
				type="primary"
				@click="$account.switchToTeam(team)"
			>
				Impersonate
			</Button>
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
