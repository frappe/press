export default [
	{
		path: '/install-app/:marketplaceApp',
		name: 'InstallMarketplaceApp',
		component: () => import('@/views/marketplace/InstallMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/user-review/:marketplaceApp',
		name: 'ReviewMarketplaceApp',
		component: () => import('@/views/marketplace/ReviewMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/marketplace',
		name: 'Marketplace',
		component: () =>
			import(
				/* webpackChunkName: "marketplace" */ '../views/marketplace/Marketplace.vue'
			),
		children: [
			{
				path: 'publisher-profile',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplacePublisherProfile.vue'
					)
			},
			{
				path: 'apps',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplaceApps.vue'
					)
			},
			{
				path: 'payouts/:payoutOrderName?',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplacePayouts.vue'
					),
				props: true
			}
		]
	},
	{
		path: '/marketplace/apps/new',
		name: 'NewMarketplaceApp',
		component: () => import('../views/marketplace/NewMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/marketplace/apps/:appName',
		name: 'MarketplaceApp',
		component: () => import('../views/marketplace/MarketplaceApp.vue'),
		props: true,
		children: [
			{
				name: 'MarketplaceAppOverview',
				path: 'overview',
				component: () =>
					import('../views/marketplace/MarketplaceAppOverview.vue')
			},
			{
				name: 'MarketplaceAppReview',
				path: 'review',
				component: () =>
					import('../views/marketplace/MarketplaceAppReview.vue'),
				props: true
			},
			{
				name: 'MarketplaceAppAnalytics',
				path: 'analytics',
				component: () =>
					import('../views/marketplace/MarketplaceAppAnalytics.vue')
			},
			{
				name: 'MarketplaceAppDeployment',
				path: 'releases',
				component: () =>
					import('../views/marketplace/MarketplaceAppDeployment.vue')
			},
			{
				name: 'MarketplaceAppSubscriptions',
				path: 'subscriptions',
				component: () =>
					import('../views/marketplace/MarketplaceAppSubscriptions.vue')
			},
			{
				name: 'MarketplaceAppPricing',
				path: 'pricing',
				component: () =>
					import('../views/marketplace/MarketplaceAppPricing.vue')
			}
		]
	}
];
