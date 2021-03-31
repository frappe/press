export default [
	{
		path: '/apps',
		name: 'Apps',
		component: () =>
			import(/* webpackChunkName: "newapp" */ '../views/Apps.vue'),
		props: true
	},
	{
		path: '/apps/new',
		name: 'NewApp',
		component: () =>
			import(/* webpackChunkName: "newapp" */ '../views/NewApp.vue'),
		props: true
	},
	{
		path: '/apps/:appName',
		name: 'App',
		component: () => import(/* webpackChunkName: "apps" */ '../App.vue'),
		props: true
	}
];
