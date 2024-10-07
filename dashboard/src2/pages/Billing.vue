<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<FBreadcrumbs
				:items="[{ label: 'Billing', route: { name: 'Billing' } }]"
			/>
		</Header>
		<TabsWithRouter
			v-if="$team?.doc?.is_desk_user || $session.hasBillingAccess"
			:tabs="tabs"
		/>
		<div
			v-else
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<i-lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage message="You aren't permitted to view the billing page" />
		</div>
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
				{ label: 'Payment Methods', route: { name: 'BillingPaymentMethods' } },
				{
					label: 'Marketplace Payouts',
					route: { name: 'BillingMarketplacePayouts' }
				}
			]
		};
	}
};
</script>
