export default [
	{
		path: '/servers',
		name: 'Servers',
		component: () => import('../views/server/Servers.vue')
	},
	{
		path: '/servers/new',
		name: 'NewServer',
		component: () => import('../views/server/NewServer.vue'),
		props: true
	},
	{
		path: '/servers/:serverName',
		name: 'Server',
		component: () => import('../views/server/Server.vue'),
		props: true,
		children: [
			{
				name: 'ServerOverview',
				path: 'overview',
				component: () => import('../views/server/ServerOverview.vue')
			},
			{
				name: 'ServerAnalytics',
				path: 'analytics',
				component: () => import('../views/server/ServerAnalytics.vue')
			},
			{
				name: 'ServerBenches',
				path: 'benches',
				component: () => import('../views/server/ServerBenches.vue')
			},
			{
				name: 'ServerJobs',
				path: 'jobs/:jobName?',
				component: () => import('../views/server/ServerJobs.vue'),
				props: true
			},
			{
				name: 'ServerPlays',
				path: 'plays/:playName?',
				component: () => import('../views/server/ServerPlays.vue'),
				props: true
			},
			{
				name: 'ServerInstall',
				path: 'install',
				component: () => import('../views/server/ServerInstall.vue'),
				props: true
			},
			{
				name: 'ServerSettings',
				path: 'setting',
				component: () => import('../views/server/ServerSettings.vue'),
				props: true
			}
		]
	},
	{
		name: 'New SelfHosted Server',
		path: '/selfhosted/new',
		component: () => import('../views/server/NewSelfHostedServer.vue'),
		props: true
	}
];
