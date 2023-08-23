<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs
				:items="[{ label: 'Billing', route: { name: 'BillingScreen' } }]"
			>
			</BreadCrumbs>
		</header>
		<div class="p-5">
			<div class="mx-auto max-w-4xl space-y-5">
				<AlertBillingInformation />
				<AccountBillingUsage />
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
