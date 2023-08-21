<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountProfile />
		<AccountEmails />
		<AccountReferral />
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountEmails from './AccountEmails.vue';

export default {
	name: 'AccountSettings',
	pageMeta() {
		return {
			title: 'Settings - Profile'
		};
	},
	components: {
		AccountProfile,
		AccountReferral,
		AccountEmails
	}
};
</script>
