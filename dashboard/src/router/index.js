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
		path: '/login/:forgot?',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/Login.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/signup',
		name: 'Signup',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/Signup.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/setup-account/:requestKey/:joinRequest?',
		name: 'Setup Account',
		component: () =>
			import(
				/* webpackChunkName: "setup-account" */ '../views/SetupAccount.vue'
			),
		props: true,
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/reset-password/:requestKey',
		name: 'Reset Password',
		component: () =>
			import(
				/* webpackChunkName: "reset-password" */ '../views/ResetPassword.vue'
			),
		props: true,
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
		path: '/support',
		name: 'Support',
		component: () =>
			import(/* webpackChunkName: "support" */ '../views/Support.vue')
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import(/* webpackChunkName: "site" */ '../views/Site.vue'),
		props: true,
		children: [
			{
				path: 'general',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteGeneral.vue')
			},
			{
				path: 'apps',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteApps.vue')
			},
			{
				path: 'domains',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteDomains.vue')
			},
			{
				path: 'analytics',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteAnalytics.vue')
			},
			{
				path: 'backups',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteBackups.vue')
			},
			{
				path: 'site-config',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteConfig.vue')
			},
			{
				path: 'console',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteConsole.vue')
			},
			{
				path: 'drop-site',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteDrop.vue')
			},
			{
				path: 'access-control',
				component: () =>
					import(
						/* webpackChunkName: "site" */ '../views/SiteAccessControl.vue'
					)
			},
			{
				path: 'jobs/:jobName?',
				component: () =>
					import(/* webpackChunkName: "site" */ '../views/SiteJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/account',
		name: 'Account',
		component: () =>
			import(/* webpackChunkName: "account" */ '../views/Account.vue'),
		children: [
			{
				path: 'profile',
				component: () =>
					import(
						/* webpackChunkName: "account" */ '../views/AccountProfile.vue'
					)
			},
			{
				path: 'team',
				component: () =>
					import(/* webpackChunkName: "account" */ '../views/AccountTeam.vue')
			},
			{
				path: 'billing',
				component: () =>
					import(
						/* webpackChunkName: "account" */ '../views/AccountBilling.vue'
					)
			}
		]
	}
];

const router = new VueRouter({
	routes
});

router.beforeEach(async (to, from, next) => {
	if (to.matched.some(record => !record.meta.isLoginPage)) {
		// this route requires auth, check if logged in
		// if not, redirect to login page.
		if (!store.auth.isLoggedIn) {
			next({ name: 'Login' });
		} else {
			if (!store.account.user) {
				await store.account.fetchAccount();
			}
			next();
		}
	} else {
		// if already logged in, route to /sites
		if (store.auth.isLoggedIn) {
			if (!store.account.user) {
				await store.account.fetchAccount();
			}
			next({ name: 'Sites' });
		} else {
			next();
		}
	}
});

export default router;
