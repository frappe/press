export default [
	{
		path: '/sites',
		name: 'Sites',
		component: () => import('../views/Sites.vue')
	},
	{
		path: '/:bench/sites',
		name: 'BenchSites',
		component: () => import('../views/Sites.vue'),
		props: true
	},
	{
		path: '/sites/new',
		name: 'NewSite',
		component: () => import('../views/NewSite.vue'),
		props: true
	},
	{
		path: '/:bench/new',
		name: 'NewBenchSite',
		component: () => import('../views/NewSite.vue'),
		props: true
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import('../views/Site.vue'),
		props: true,
		children: [
			{
				name: 'SiteOverview',
				path: 'overview',
				component: () => import('../views/SiteOverview.vue')
			},
			{
				path: 'installing',
				component: () => import('../views/SiteInstalling.vue')
			},
			{
				path: 'analytics',
				component: () => import('../views/SiteCharts.vue')
			},
			{
				path: 'database',
				component: () => import('../views/SiteDatabase.vue')
			},
			{
				path: 'site-config',
				component: () => import('../views/SiteConfig.vue')
			},
			{
				path: 'console',
				component: () => import('../views/SiteConsole.vue')
			},
			{
				path: 'activity',
				component: () => import('../views/SiteActivity.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/SiteJobs.vue'),
				props: true
			},
			{
				path: 'logs/:logName?',
				component: () => import('../views/SiteLogs.vue'),
				props: true
			},
			{
				path: 'request-logs',
				component: () => import('../views/SiteRequestLogs.vue'),
				props: true
			},
			{
				path: 'auto-update',
				component: () => import('../views/SiteAutoUpdate.vue'),
				props: true
			}
		]
	}
];
