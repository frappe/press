export default {
	path: '/billing/:invoiceName?',
	name: 'BillingScreen',
	component: () => import('../views/billing/AccountBilling.vue'),
	props: true
};
