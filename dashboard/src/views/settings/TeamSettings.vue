<template>
	<div
		v-if="$account.user.name === $account.team.user"
		class="grid grid-cols-1 gap-5 md:grid-cols-2"
	>
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
