export default [
	{
		path: '/sites',
		name: 'Sites',
		component: () =>
			import(/* webpackChunkName: "sites" */ '../views/Sites.vue')
	},
	{
		path: '/sites/new',
		name: 'NewSite',
		component: () =>
			import(/* webpackChunkName: "newsite" */ '../views/NewSite/Index.vue'),
		props: true
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import(/* webpackChunkName: "site" */ '../views/Site.vue'),
		props: true,
		children: [
			{
				name: 'SiteOverview',
				path: 'overview',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteOverview.vue')
			},
			{
				path: 'installing',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteInstalling.vue')
			},
			{
				path: 'analytics',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteAnalytics.vue')
			},
			{
				path: 'backups',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteBackups.vue')
			},
			{
				path: 'database',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteDatabase.vue')
			},
			{
				path: 'site-config',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteConfig.vue')
			},
			{
				path: 'console',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteConsole.vue')
			},
			{
				path: 'activity',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteActivity.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteJobs.vue'),
				props: true
			},
			{
				path: 'logs/:logName?',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteLogs.vue'),
				props: true
			},
			{
				path: 'request-logs',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteRequestLogs.vue'),
				props: true
			}
		]
	}
];
