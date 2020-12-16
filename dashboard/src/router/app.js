export default [
	{
		path: '/apps',
		name: 'Apps',
		component: () => import(/* webpackChunkName: "apps" */ '../views/Apps.vue')
	},
	{
		path: '/apps/:appName(.*)',
		name: 'App',
		component: () =>
			import(/* webpackChunkName: "frappeapp" */ '../views/App.vue'),
		props: true,
		children: [
			{
				path: 'general',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppGeneral.vue')
			},
			{
				path: 'releases',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppReleases.vue')
			},
			{
				path: 'sources',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppSources.vue')
			},
			{
				path: 'marketplace',
				component: () =>
					import(
						/* webpackChunkName: "frappeapp" */ '../views/AppMarketplace.vue'
					)
			}
		]
	}
];
