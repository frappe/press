<template>
	<div class="px-4 py-4 text-base sm:px-8">Impersonating {{ teamId }}</div>
</template>
<script>
import { switchToTeam } from '../data/team';
export default {
	name: 'Impersonate',
	props: ['teamId'],
	async mounted() {
		if (this.teamId && this.teamId !== this.$team.name) {
			switchToTeam(this.teamId);
		} else {
			if (window.history.length > 1) {
				this.$router.back();
			} else {
				this.$router.replace('/');
			}
		}
	}
};
</script>
