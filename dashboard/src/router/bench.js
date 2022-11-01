export default [
	{
		path: '/benches',
		name: 'BenchesScreen',
		component: () => import('../views/bench/Benches.vue')
	},
	{
		path: '/benches/new/:saas_app?',
		name: 'NewBench',
		meta: {
			isSaasPage: true
		},
		component: () => import('../views/bench/NewBench.vue'),
		props: true
	},
	{
		path: '/servers/:server/bench/new',
		name: 'NewServerBench',
		component: () => import('../views/bench/NewBench.vue'),
		props: true
	},
	{
		path: '/benches/:benchName',
		name: 'Bench',
		component: () => import('../views/bench/Bench.vue'),
		props: true,
		meta: {
			isSaasPage: true
		},
		children: [
			{
				path: 'overview',
				component: () => import('../views/bench/BenchOverview.vue')
			},
			{
				path: 'apps',
				component: () => import('../views/bench/BenchApps.vue'),
				props: true
			},
			{
				path: 'versions/:version?',
				component: () => import('../views/bench/BenchVersions.vue'),
				props: true
			},
			{
				path: 'deploys/:candidateName?',
				component: () => import('../views/bench/BenchDeploys.vue'),
				props: true
			},
			{
				path: 'logs/:instanceName/:logName?',
				component: () => import('../views/bench/BenchLogs.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/bench/BenchJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/benches/:benchName/apps/new',
		name: 'NewBenchApp',
		component: () => import('../views/bench/NewBenchApp.vue'),
		props: true
	}
];
