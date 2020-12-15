export default {
	path: '/account',
	name: 'Account',
	component: () =>
		import(/* webpackChunkName: "account" */ '../views/Account.vue'),
	children: [
		{
			path: 'profile',
			component: () =>
				import(/* webpackChunkName: "account" */ '../views/AccountProfile.vue')
		},
		{
			path: 'team',
			component: () =>
				import(/* webpackChunkName: "account" */ '../views/AccountTeam.vue')
		},
		{
			path: 'billing',
			component: () =>
				import(/* webpackChunkName: "account" */ '../views/AccountBilling.vue')
		}
	]
};
