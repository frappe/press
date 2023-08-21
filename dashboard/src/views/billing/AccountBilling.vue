<template>
	<div>
		<div class="space-y-5">
			<AlertBillingInformation />
			<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
				<AccountBillingUsage class="col-span-1 md:col-span-2" />
				<AccountBillingDetails />
				<AccountBillingCards />
				<AccountBillingPayments
					class="col-span-1 md:col-span-2"
					:invoice-name="invoiceName"
				/>
				<AccountBillingCreditBalance class="col-span-1 md:col-span-2" />
			</div>
		</div>
	</div>
</template>

<script>
import AccountBillingUsage from './AccountBillingUsage.vue';
import AccountBillingDetails from './AccountBillingDetails.vue';
import AccountBillingCards from './AccountBillingCards.vue';
import AccountBillingPayments from './AccountBillingPayments.vue';
import AccountBillingCreditBalance from './AccountBillingCreditBalance.vue';
import AlertBillingInformation from '@/components/AlertBillingInformation.vue';

export default {
	name: 'BillingScreen',
	pageMeta() {
		return {
			title: 'Billing - Frappe Cloud'
		};
	},
	props: ['invoiceName'],
	components: {
		AccountBillingUsage,
		AccountBillingDetails,
		AccountBillingCards,
		AccountBillingPayments,
		AccountBillingCreditBalance,
		AlertBillingInformation
	}
};
</script>
