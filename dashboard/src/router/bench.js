export default [
	{
		path: '/benches',
		name: 'Benches',
		component: () =>
			import(/* webpackChunkName: "benches" */ '../views/Benches.vue')
	},
	{
		path: '/benches/new',
		name: 'NewBench',
		component: () =>
			import(/* webpackChunkName: "newbench" */ '../views/NewBench.vue'),
		props: true
	},
	{
		path: '/benches/:benchName',
		name: 'Bench',
		component: () =>
			import(/* webpackChunkName: "bench" */ '../views/Bench.vue'),
		props: true,
		children: [
			{
				path: 'general',
				component: () =>
					import(/* webpackChunkName: "bench" */ '../views/BenchGeneral.vue')
			},
			{
				path: 'apps',
				component: () =>
					import(/* webpackChunkName: "bench" */ '../views/BenchApps.vue')
			},
			{
				path: 'deploys/:candidateName?',
				component: () =>
					import(/* webpackChunkName: "bench" */ '../views/BenchDeploys.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () =>
					import(/* webpackChunkName: "bench" */ '../views/BenchJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/benches/:benchName/apps/new',
		name: 'NewApp',
		component: () =>
			import(/* webpackChunkName: "bench" */ '../views/NewApp.vue'),
		props: true
	}
];
