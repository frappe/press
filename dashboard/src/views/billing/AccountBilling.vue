<template>
	<div>
		<header class="sticky top-0 z-10 border-b bg-white px-5 pt-2.5">
			<Breadcrumbs
				:items="[{ label: 'Billing', route: { name: 'BillingScreen' } }]"
			/>
			<Tabs :tabs="tabs" class="-mb-px pl-0.5" />
		</header>
		<div class="mx-auto max-w-5xl py-5">
			<router-view />
		</div>
	</div>
</template>

<script>
import Tabs from '@/components/Tabs.vue';

export default {
	name: 'BillingScreen',
	pageMeta() {
		return {
			title: 'Billing - Frappe Cloud'
		};
	},
	props: ['invoiceName'],
	components: {
		Tabs
	},
	computed: {
		tabs() {
			let tabRoute = subRoute => `/billing/${subRoute}`;
			let tabs = [
				{ label: 'Overview', route: 'overview' },
				{ label: 'Invoices', route: 'invoices' },
				{ label: 'Payment Methods', route: 'payment' },
				{ label: 'Credit Balance', route: 'credit-balance' }
			];

			return tabs.map(tab => {
				return {
					...tab,
					route: tabRoute(tab.route)
				};
			});
		}
	}
};
</script>
