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
				name: 'ServerJobs',
				path: 'jobs/:jobName?',
				component: () => import('../views/server/ServerJobs.vue'),
				props: true
			}
		]
	}
];
