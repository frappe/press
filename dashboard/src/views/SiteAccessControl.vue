<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Login</h2>
			<p class="text-gray-600">Login directly to your site as Administrator</p>
			<Button
				class="mt-6 border hover:bg-gray-100"
				@click="loginAsAdministrator"
				:disabled="state === 'Logging In'"
			>
				Login as Administrator
			</Button>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Reset password</h2>
			<p class="text-gray-600">Send a password reset email for Administrator</p>
			<Button class="mt-6 border hover:bg-gray-100">Reset Password</Button>
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
			let sid = await this.$call('press.api.site.login', {
				name: this.site.name
            });
            if (sid) {
                window.open(`https://${this.site.name}/desk?sid=${sid}`, '_blank');
            }
			this.state = null;
		}
	}
};
</script>
