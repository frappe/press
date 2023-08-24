<template>
	<div v-if="$account.user.name === $account.team.user" class="space-y-5">
		<AccountMembers />
		<AccountGroups />
	</div>
</template>

<script>
import AccountGroups from './AccountGroups.vue';
import AccountMembers from './AccountMembers.vue';

export default {
	name: 'AccountSettings',
	pageMeta() {
		return {
			title: 'Settings - Team'
		};
	},
	components: {
		AccountMembers,
		AccountGroups
	}
};
</script>
