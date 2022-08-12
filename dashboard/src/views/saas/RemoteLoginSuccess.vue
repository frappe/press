<template>
	<div class="mt-10 text-center text-sm"></div>
</template>

<script>
export default {
	name: 'RemoteLogin',
	methods: {
		login: () => {
			const params = new URLSearchParams(window.location.search)
			localStorage.setItem('current_team', params.get("team"))
			localStorage.setItem('saas_login', true);
			window.location.href = '/dashboard/saas/apps';
		}
	},
	created() {
		this.login();
	}
};
</script>
