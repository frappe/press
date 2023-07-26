export default [
	{
		path: '/spaces',
		name: 'Spaces',
		component: () => import('../views/spaces/Spaces.vue')
	},
	{
		path: '/codeservers/:serverName',
		name: 'CodeServer',
		component: () => import('../views/spaces/CodeServer.vue'),
		props: true,
		children: [
			{
				name: 'CodeServerOverview',
				path: 'overview',
				component: () => import('../views/spaces/CodeServerOverview.vue')
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/spaces/CodeServerJobs.vue'),
				props: true
			}
		]
	}
];
