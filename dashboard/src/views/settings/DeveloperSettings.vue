<template>
	<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
		<AccountAPI />
		<AccountSSHKey />
	</div>
</template>

<script>
import AccountAPI from './AccountAPI.vue';
import AccountSSHKey from './AccountSSHKey.vue';

export default {
	name: 'DeveloperSettings',
	pageMeta() {
		return {
			title: 'Settings - Developer'
		};
	},
	components: {
		AccountAPI,
		AccountSSHKey
	}
};
</script>
