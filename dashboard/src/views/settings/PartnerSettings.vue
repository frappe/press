<template>
	<div class="mx-auto max-w-4xl space-y-5">
		<AccountPartner />
		<PartnerReferral />
		<PartnerCustomers class="col-span-1 md:col-span-2" />
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
