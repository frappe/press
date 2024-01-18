<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[{ label: 'Billing', route: { name: 'Billing' } }]"
			/>
		</Header>
		<TabsWithRouter :tabs="tabs" />
	</div>
</template>
<script>
import { Tabs, Breadcrumbs } from 'frappe-ui';
import Header from '../components/Header.vue';
import TabsWithRouter from '../components/TabsWithRouter.vue';

export default {
	name: 'Billing',
	components: {
		Header,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
		TabsWithRouter
	},
	data() {
		return {
			currentTab: 0,
			tabs: [
				{ label: 'Overview', route: { name: 'BillingOverview' } },
				{ label: 'Invoices', route: { name: 'BillingInvoices' } },
				{ label: 'Balances', route: { name: 'BillingBalances' } },
				{ label: 'Payment Methods', route: { name: 'BillingPaymentMethods' } }
			]
		};
	}
};
</script>
