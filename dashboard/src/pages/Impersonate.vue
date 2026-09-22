<template>
	<div class="px-4 py-4 text-base sm:px-8">Impersonating {{ teamId }}</div>
</template>
<script>
import { getCurrentTeam } from '../data/currentTeam'
import { impersonateTeam } from '../data/team'
export default {
	name: 'Impersonate',
	props: ['teamId'],
	async mounted() {
		// Open this route in a new tab to impersonate a team there without
		// disturbing the team the other tabs are on.
		if (this.teamId && this.teamId !== getCurrentTeam()) {
			impersonateTeam(this.teamId)
		} else if (window.history.length > 1) {
			this.$router.back()
		} else {
			this.$router.replace('/')
		}
	},
}
</script>
