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
			window.location.href = `/dashboard/sites/${params.get("site")}/overview`;
		}
	},
	created() {
		this.login();
	}
};
</script>
