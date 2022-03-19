export default [
	{
		path: '/saas/login/:forgot?',
		name: 'SaasLogin',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/saas/SaasLogin.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/saas/billing',
		name: 'SaasBilling',
		component: () => import('../views/saas/SaasBilling.vue')
	},
	{
		path: '/saas/upgrade',
		name: 'SaasUpgrade',
		component: () => import('../views/saas/SaasUpgrade.vue')
	},
	{
		path: '/saas/settings',
		name: 'SaasSettings',
		component: () => import('../views/saas/SaasSettings.vue')
	}
];
