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
	}
];
