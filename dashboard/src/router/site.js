export default [
	{
		path: '/sites',
		name: 'Sites',
		component: () => import('../views/site/Sites.vue')
	},
	{
		path: '/:bench/sites',
		name: 'BenchSites',
		component: () => import('../views/site/Sites.vue'),
		props: true
	},
	{
		path: '/sites/new',
		name: 'NewSite',
		component: () => import('../views/site/NewSite.vue'),
		props: true
	},
	{
		path: '/:bench/new',
		name: 'NewBenchSite',
		component: () => import('../views/site/NewSite.vue'),
		props: true
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import('../views/site/Site.vue'),
		props: true,
		children: [
			{
				name: 'SiteOverview',
				path: 'overview',
				component: () => import('../views/site/SiteOverview.vue')
			},
			{
				name: 'SiteOverviewAppsAndSubscriptions',
				path: 'apps',
				component: () =>
					import('../views/site/SiteOverviewAppsAndSubscriptions.vue'),
				props: true
			},
			{
				path: 'installing',
				component: () => import('../views/site/SiteInstalling.vue')
			},
			{
				path: 'analytics',
				component: () => import('../views/site/SiteCharts.vue')
			},
			{
				path: 'database',
				component: () => import('../views/site/SiteDatabase.vue')
			},
			{
				path: 'site-config',
				component: () => import('../views/site/SiteConfig.vue')
			},
			{
				path: 'console',
				component: () => import('../views/site/SiteConsole.vue')
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/site/SiteJobs.vue'),
				props: true
			},
			{
				path: 'logs/:logName?',
				component: () => import('../views/site/SiteLogs.vue'),
				props: true
			},
			{
				path: 'request-logs',
				component: () => import('../views/site/SiteRequestLogs.vue'),
				props: true
			},
			{
				path: 'auto-update',
				component: () => import('../views/site/SiteAutoUpdate.vue'),
				props: true
			}
		]
	}
];
