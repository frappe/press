<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountProfile />
		<AccountTeam />
		<AccountMembers />
	</div>
</template>

<script>
import AccountProfile from './AccountProfile.vue';
import AccountTeam from './AccountTeam.vue';
import AccountMembers from './AccountMembers.vue';

export default {
	name: 'AccountProfileTeam',
	props: ['account'],
	components: {
		AccountProfile,
		AccountTeam,
		AccountMembers
	}
};
</script>
