<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountProfile />
		<AccountTeam />
		<AccountMembers />
		<AccountActions />
		<AccountReferral />
		<AccountEmails />
		<AccountSSHKey />
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountTeam from './AccountTeam.vue';
import AccountMembers from './AccountMembers.vue';
import AccountActions from './AccountActions.vue';
import AccountReferral from './AccountReferral.vue';
import AccountEmails from './AccountEmails.vue';
import AccountSSHKey from './AccountSSHKey.vue';

export default {
	name: 'AccountProfileTeam',
	props: ['account'],
	components: {
		AccountActions,
		AccountProfile,
		AccountTeam,
		AccountMembers,
		AccountReferral,
		AccountEmails,
		AccountSSHKey
	}
};
</script>
