<template>
	<div class="mt-10 text-center text-sm">
		<Button
			:loading="true"
			loading-text="Loading..."
			v-if="this.$resources.login.loading"
		/>
	</div>
</template>

<script>
export default {
	name: 'RemoteLogin',
	resources: {
		login() {
			return {
				method: 'press.api.saas.login_via_token',
				params: {
					token: this.$route.query.token
				},
				onSuccess(r) {
					this.$saas.saasLogin();
					window.location.href = '/dashboard/saas/apps';
				},
				onError(e) {
					this.$notify({
						title: 'Token expired or invalid!',
						subtitle: e,
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	},
	created() {
		this.$resources.login.submit();
	}
};
</script>
