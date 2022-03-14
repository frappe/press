<template>
	<Alert
		title="Site Activation"
		v-if="site.status == 'Active' && !site.setup_wizard_complete"
	>
		<span>
			Please login and complete the setup wizard on your site. Analytics will be
			collected only after setup is complete.
		</span>
		<template #actions>
			<Button
				type="primary"
				@click="$resources.loginAsAdmin.submit()"
				:loading="$resources.loginAsAdmin.loading"
			>
				Login
			</Button>
		</template>
	</Alert>
</template>
<script>
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
export default {
	name: 'AlertSiteActivation',
	props: ['site'],
	resources: {
		loginAsAdmin() {
			return loginAsAdmin(this.site.name);
		}
	}
};
</script>
