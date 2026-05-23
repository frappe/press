<template>
	<div class="mx-auto mt-16 max-w-xl space-y-4">
		<h1 class="text-center text-2xl font-semibold">Activer la 2FA</h1>

		<AlertBanner
			:title="`L'authentification à deux facteurs est obligatoire pour tous les membres de l'équipe <strong>${$team.doc.user}</strong> par le propriétaire/admin de l'équipe. Vous devez l'activer pour continuer.`"
			type="error"
		/>
		<Configure2FA @enabled="handleEnabled" />
	</div>
</template>

<script>
import Configure2FA from '../components/auth/Configure2FA.vue';
import AlertBanner from '../components/AlertBanner.vue';

export default {
	components: {
		Configure2FA,
		AlertBanner,
	},
	methods: {
		handleEnabled() {
			this.$team.reload();

			// sometimes the reload is too fast
			// and the user is not redirected back here due to the 2FA requirement
			setTimeout(() => {
				this.$router.push({ name: 'Site List' });
			}, 100);
		},
	},
};
</script>
