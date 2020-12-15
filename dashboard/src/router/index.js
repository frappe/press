import Vue from 'vue';
import VueRouter from 'vue-router';
import account from '../controllers/account';
import auth from '../controllers/auth';
import Home from '../views/Home.vue';

import appRoutes from './app';
import siteRoutes from './site';
import accountRoute from './account';
import authRoutes from './auth';

Vue.use(VueRouter);

const routes = [
	{
		path: '/',
		name: 'Home',
		component: Home
	},
	{
		path: '/welcome',
		name: 'Welcome',
		component: () =>
			import(/* webpackChunkName: "sites" */ '../views/Welcome.vue')
	},
	{
		path: '/apps',
		name: 'Apps',
		component: () => import(/* webpackChunkName: "apps" */ '../views/Apps.vue')
	},
	{
		path: '/apps/:appName(.*)',
		name: 'App',
		component: () =>
			import(/* webpackChunkName: "frappeapp" */ '../views/App.vue'),
		props: true,
		children: [
			{
				path: 'general',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppGeneral.vue')
			},
			{
				path: 'sources',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppSources.vue')
			},
			{
				path: 'releases',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppReleases.vue')
			},
			{
				path: 'deploys',
				component: () =>
					import(/* webpackChunkName: "frappeapp" */ '../views/AppDeploys.vue')
			}
		]
	},
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
			}
		]
	},
	{
		path: '/benches/:benchName/apps/new',
		name: 'NewApp',
		component: () =>
			import(/* webpackChunkName: "bench" */ '../views/NewApp.vue'),
		props: true
	},
	{
		path: '/sites',
		name: 'Sites',
		component: () =>
			import(/* webpackChunkName: "sites" */ '../views/Sites.vue')
	},
	{
		path: '/sites/new',
		name: 'NewSite',
		component: () =>
			import(/* webpackChunkName: "newsite" */ '../views/NewSite/Index.vue'),
		props: true
	},
	{
		path: '/support',
		name: 'Support',
		component: () =>
			import(/* webpackChunkName: "support" */ '../views/Support.vue')
	},
	...authRoutes,
	...appRoutes,
	...siteRoutes,
	accountRoute
];

const router = new VueRouter({
	routes
});

router.beforeEach(async (to, from, next) => {
	if (to.name == 'Home') {
		next({ name: 'Welcome' });
		return;
	}

	if (to.matched.some(record => !record.meta.isLoginPage)) {
		// this route requires auth, check if logged in
		// if not, redirect to login page.
		if (!auth.isLoggedIn) {
			next({ name: 'Login', query: { route: to.path } });
		} else {
			if (!account.user) {
				await account.fetchAccount();
			}
			next();
		}
	} else {
		// if already logged in, route to /welcome
		if (auth.isLoggedIn) {
			if (!account.user) {
				await account.fetchAccount();
			}
			next({ name: 'Welcome' });
		} else {
			next();
		}
	}
});

export default router;
