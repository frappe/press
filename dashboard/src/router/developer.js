export default [
	{
		path: '/developer',
		name: 'Developer',
		component: () =>
			import(/* webpackChunkName: "developer" */ '../views/Developer.vue'),
		children: [
			{
				path: 'profile',
				component: () =>
					import(
						/* webpackChunkName: "developer" */ '../views/DeveloperApps.vue'
					)
			},
			{
				path: 'apps',
				component: () =>
					import(
						/* webpackChunkName: "developer" */ '../views/DeveloperApps.vue'
					)
			}
		]
	},
	{
		path: '/developer/apps/:appName',
		name: 'DeveloperApp',
		component: () => import('../views/DeveloperApp.vue'),
		props: true,
		children: [
			{
				name: 'DeveloperAppOverview',
				path: 'overview',
				component: () => import('../views/SiteOverview.vue')
			},
			{
				path: 'analytics',
				component: () => import('../views/SiteCharts.vue')
			}
		]
	}
];
