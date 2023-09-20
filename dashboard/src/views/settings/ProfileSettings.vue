<template>
	<div class="space-y-5">
		<AccountProfile />
		<AccountEmails />
		<AccountReferral />
		<AccountPartner />
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountReferral from './AccountReferral.vue';
import AccountEmails from './AccountEmails.vue';
import AccountPartner from './AccountPartner.vue';

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
		AccountPartner
	}
};
</script>
