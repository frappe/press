export default [
	{
		path: '/apps',
		name: 'Apps',
		component: () => import(/* webpackChunkName: "apps" */ '../views/Apps.vue')
	},
	{
		path: '/apps/new',
		name: 'NewApp',
		component: () =>
			import(/* webpackChunkName: "newapp" */ '../views/NewApp.vue'),
		props: true
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
				path: 'deploys',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppDeploys.vue')
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
