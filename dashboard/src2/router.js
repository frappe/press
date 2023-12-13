import { createRouter, createWebHistory } from 'vue-router';
import generateRoutes from './objects/generateRoutes';

let router = createRouter({
	history: createWebHistory('/dashboard2/'),
	routes: [
		{
			path: '/',
			name: 'Home',
			component: () => import('./pages/Home.vue')
		},
		{
			path: '/login',
			name: 'Login',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true }
		},
		{
			path: '/signup',
			name: 'Signup',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true }
		},
		{
			path: '/setup-account/:requestKey/:joinRequest?',
			name: 'Setup Account',
			component: () => import('./pages/SetupAccount.vue'),
			props: true,
			meta: { isLoginPage: true }
		},
		{
			path: '/reset-password/:requestKey',
			name: 'Reset Password',
			component: () => import('./pages/ResetPassword.vue'),
			props: true,
			meta: { isLoginPage: true }
		},
		{
			name: 'JobPage',
			path: '/jobs/:id',
			component: () => import('./pages/JobPage.vue'),
			props: true
		},
		{
			name: 'NewSite',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue')
		},
		{
			name: 'NewBench',
			path: '/benches/new',
			component: () => import('./pages/NewBench.vue')
		},
		...generateRoutes()
	]
});

router.beforeEach((to, from, next) => {
	let isLoggedIn =
		document.cookie.includes('user_id') &&
		!document.cookie.includes('user_id=Guest;');

	if (to.matched.some(record => record.meta.isLoginPage)) {
		if (isLoggedIn) {
			next({ name: 'Home' });
		} else {
			next();
		}
	} else {
		if (isLoggedIn) {
			next();
		} else {
			next({ name: 'Login' });
		}
	}
});

export default router;
