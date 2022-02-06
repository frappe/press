export default {
	path: '/account',
	name: 'Account',
	component: () =>
		import(/* webpackChunkName: "account" */ '../views/Account.vue'),
	children: [
		{
			path: 'profile',
			component: () =>
				import(
					/* webpackChunkName: "account" */ '../views/AccountProfileTeam.vue'
				)
		},
		{
			path: 'billing/:invoiceName?',
			component: () =>
				import(/* webpackChunkName: "account" */ '../views/AccountBilling.vue'),
			props: true
		}
	]
};
