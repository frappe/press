import Vue from 'vue';
import VueRouter from 'vue-router';
import account from '../controllers/account';
import auth from '../controllers/auth';
import Home from '../views/Home.vue';

import siteRoutes from './site';
import benchRoutes from './bench';
import accountRoute from './account';
import authRoutes from './auth';
import marketplaceRoutes from './marketplace';

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
		component: () => import('../views/Welcome.vue')
	},
	...authRoutes,
	...benchRoutes,
	...siteRoutes,
	...marketplaceRoutes,
	accountRoute
];

const router = new VueRouter({
	base: '/dashboard/',
	mode: 'history',
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
