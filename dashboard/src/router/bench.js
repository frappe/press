export default [
	{
		path: '/benches/new',
		name: 'NewBench',
		component: () => import('../views/NewBench.vue'),
		props: true
	},
	{
		path: '/benches/:benchName',
		name: 'Bench',
		component: () => import('../views/Bench.vue'),
		props: true,
		children: [
			{
				path: 'overview',
				component: () => import('../views/BenchOverview.vue')
			},
			{
				path: 'apps',
				component: () => import('../views/BenchApps.vue')
			},
			{
				path: 'deploys/:candidateName?',
				component: () => import('../views/BenchDeploys.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/BenchJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/benches/:benchName/apps/new',
		name: 'NewApp',
		component: () => import('../views/NewApp.vue'),
		props: true
	}
];
