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
			<Button type="primary" @click="loginAsAdministrator(site.name)">
				Login
			</Button>
		</template>
	</Alert>
</template>
<script>
export default {
	name: 'AlertSiteActivation',
	props: ['site'],
	inject: ['loginAsAdministrator']
};
</script>
