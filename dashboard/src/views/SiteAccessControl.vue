<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Login</h2>
			<p class="text-gray-600">Login directly to your site as Administrator</p>
			<Button
				class="mt-6"
				@click="loginAsAdministrator"
				:disabled="state === 'Logging In'"
			>
				Login as Administrator
			</Button>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteAccessControl',
	props: ['site'],
	data: () => ({
		state: null
	}),
	methods: {
		async loginAsAdministrator() {
			this.state = 'Logging In';
			await this.$store.sites.loginAsAdministrator(this.site.name);
			this.state = null;
		}
	}
};
</script>
