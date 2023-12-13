<template>
	<div class="space-y-5">
		<AlertBillingInformation />
		<BillingSummary />
	</div>
</template>

<script>
import BillingSummary from './BillingSummary.vue';
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
		BillingSummary,
		AlertBillingInformation
	}
};
</script>
