<template>
	<div class="space-y-5">
		<AccountPartner />
		<PartnerReferral />
		<PartnerCustomers />
	</div>
</template>

<script>
import PartnerCustomers from '../billing/PartnerCustomers.vue';
import AccountPartner from './AccountPartner.vue';
import PartnerReferral from './PartnerReferral.vue';

export default {
	name: 'PartnerSettings',
	pageMeta() {
		return {
			title: 'Settings - Partner'
		};
	},
	components: {
		AccountPartner,
		PartnerCustomers,
		PartnerReferral
	}
};
</script>
