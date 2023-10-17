<template>
	<div class="space-y-5">
		<AlertBillingInformation />
		<AccountBillingUsage />
	</div>
</template>

<script>
import AccountBillingUsage from './AccountBillingUsage.vue';
import AccountBillingDetails from './AccountBillingDetails.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'BillingOverview',
	pageMeta() {
		return {
			title: 'Billing - Frappe Cloud'
		};
	},
	props: ['invoiceName'],
	components: {
		AccountBillingUsage,
		AlertBillingInformation
	}
};
</script>
