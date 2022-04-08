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
		path: '/saas/setting',
		name: 'SaasSetting',
		component: () => import('../views/saas/SaasSetting.vue')
	}
];
