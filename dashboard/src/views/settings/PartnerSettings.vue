<template>
	<div class="space-y-5">
		<AccountPartner />
	</div>
</template>

<script>
import AccountPartner from './AccountPartner.vue';

export default {
	name: 'PartnerSettings',
	pageMeta() {
		return {
			title: 'Settings - Partner'
		};
	},
	components: {
		AccountPartner
	}
};
</script>
