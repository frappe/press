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
		name: 'Billing',
		component: () => import('../views/saas/Billing.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/subscription',
		name: 'SaasSubscription',
		component: () => import('../views/saas/SubscriptionList.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/subscription/:subName',
		name: 'Subscription',
		component: () => import('../views/saas/Subscription.vue'),
		meta: {
			isSaasPage: true
		},
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
				component: () => import('../views/SiteDatabase.vue')
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/saas/SiteJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/saas/new-subscription',
		name: 'NewSubscription',
		component: () => import('../views/saas/NewSubscription.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/settings',
		name: 'Settings',
		component: () => import('../views/saas/Settings.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/manage',
		name: 'AppList',
		component: () => import('../views/saas/AppList.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/manage/new',
		name: 'NewSaasApp',
		component: () => import('../views/saas/NewSaasApp.vue'),
		meta: {
			isSaasPage: true
		}
	},
	{
		path: '/saas/manage/:appName',
		name: 'SaasApp',
		component: () => import('../views/saas/SaasApp.vue'),
		meta: {
			isSaasPage: true
		},
		props: true,
		children: [
			{
				path: 'overview',
				component: () => import('../views/saas/AppOverview.vue')
			},
			{
				path: 'benches',
				component: () => import('../views/saas/AppBenches.vue')
			},
			{
				path: 'plan',
				component: () => import('../views/saas/AppPlan.vue')
			}
		]
	}
];
