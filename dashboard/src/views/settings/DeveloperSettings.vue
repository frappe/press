<template>
	<div class="space-y-5">
		<AccountAPI />
		<AccountSSHKey />
		<FeatureFlags />
	</div>
</template>

<script>
import AccountAPI from './AccountAPI.vue';
import AccountSSHKey from './AccountSSHKey.vue';
import FeatureFlags from './FeatureFlags.vue';

export default {
	name: 'DeveloperSettings',
	pageMeta() {
		return {
			title: 'Settings - Developer'
		};
	},
	components: {
		AccountAPI,
		AccountSSHKey,
		FeatureFlags
	}
};
</script>
