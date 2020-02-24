import Vue from 'vue';
import VueRouter from 'vue-router';
import store from '../store';
import Home from '../views/Home.vue';

Vue.use(VueRouter);

const routes = [
	{
		path: '/',
		name: 'Home',
		component: Home
	},
	{
		path: '/login',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/Login.vue'),
		meta: {
			isLoginPage: true
		}
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
			import(/* webpackChunkName: "newsite" */ '../views/NewSite.vue'),
		props: true
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import(/* webpackChunkName: "site" */ '../views/Site.vue'),
		props: true,
		children: [
			{
				path: 'general',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteGeneral.vue'),
			},
			{
				path: 'analytics',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteAnalytics.vue'),
			},
			{
				path: 'backups',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteBackups.vue'),
			},
			{
				path: 'site-config',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteConfig.vue'),
			},
			{
				path: 'console',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteConsole.vue'),
			},
			{
				path: 'drop-site',
				component: () => import(/* webpackChunkName: "site" */ '../views/SiteDrop.vue'),
			},
			{
				path: '*',
				component: () => import(/* webpackChunkName: "site" */ '../views/ComingSoon.vue'),
			},
		]
	}
];

const router = new VueRouter({
	routes
});

router.beforeEach((to, from, next) => {
	if (to.matched.some(record => !record.meta.isLoginPage)) {
		// this route requires auth, check if logged in
		// if not, redirect to login page.
		if (!store.auth.isLoggedIn) {
			next({ name: 'Login' });
		} else {
			next();
		}
	} else {
		next();
	}
});

export default router;
