<template>
	<div class="px-4 py-4 text-base sm:px-8">Impersonating {{ team }}</div>
</template>
<script>
export default {
	name: 'ImpersonateTeam',
	props: ['team'],
	async mounted() {
		if (this.team) {
			try {
				await this.$account.switchTeam(this.team);
				if (window.history.length === 1) {
					this.$router.replace('/');
				} else {
					this.$router.back();
				}
			} catch (error) {
				this.$router.replace('/');
			}
		}
	}
};
</script>
