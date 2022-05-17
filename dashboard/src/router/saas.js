export default [
	{
		path: '/saas/login/:forgot?',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/saas/Login.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/saas/billing',
		name: 'Billing',
		component: () => import('../views/saas/Billing.vue')
	},
	{
		path: '/saas/subscription',
		name: 'SaasSubscription',
		component: () => import('../views/saas/SubscriptionList.vue')
	},
	{
		path: '/saas/subscription/:subName',
		name: 'Subscription',
		component: () => import('../views/saas/Subscription.vue'),
		props: true,
		children: [
			{
				path: 'overview',
				component: () => import('../views/saas/SubscriptionOverview.vue')
			},
			{
				path: 'plan',
				component: () => import('../views/saas/SubscriptionPlan.vue')
			},
			{
				path: 'database',
				component: () => import('../views/saas/SubscriptionDatabase.vue')
			}
		]
	},
	{
		path: '/saas/new-subscription',
		name: 'NewSubscription',
		component: () => import('../views/saas/NewSubscription.vue')
	},
	{
		path: '/saas/settings',
		name: 'Settings',
		component: () => import('../views/saas/Settings.vue')
	},
	{
		path: '/saas/manage',
		name: 'Manage',
		component: () => import('../views/saas/Manage.vue')
	},
	{
		path: '/saas/manage/:appName',
		name: 'SaasApp',
		component: () => import('../views/saas/SaasApp.vue'),
		props: true,
		children: [
			{
				path: 'overview',
				component: () => import('../views/saas/AppOverview.vue')
			},
			{
				path: 'plan',
				component: () => import('../views/saas/AppPlan.vue')
			},
		]
	}
];
