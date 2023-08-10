<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountProfile />
		<AccountEmails />
		<AccountReferral />
		<AccountAPI />
		<AccountSSHKey />
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountEmails from './AccountEmails.vue';
import AccountAPI from './AccountAPI.vue';
import AccountSSHKey from './AccountSSHKey.vue';

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
		AccountEmails,
		AccountAPI,
		AccountSSHKey
	}
};
</script>
