import { createRouter, createWebHistory } from 'vue-router';
import generateRoutes from './objects/generateRoutes';
import { getTeam } from './data/team';

let router = createRouter({
	history: createWebHistory('/dashboard2/'),
	routes: [
		{
			path: '/',
			name: 'Home',
			component: () => import('./pages/Home.vue'),
			redirect: { name: 'Welcome' }
		},
		{
			path: '/welcome',
			name: 'Welcome',
			component: () => import('./pages/Welcome.vue')
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
		{
			name: 'NewAppSite',
			path: '/new-app-site',
			component: () => import('./pages/NewAppSite.vue')
		},
		...generateRoutes(),
		{
			path: '/:pathMatch(.*)*',
			name: '404',
			component: () => import('../src/views/general/404.vue')
		}
	]
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn =
		document.cookie.includes('user_id') &&
		!document.cookie.includes('user_id=Guest;');
	let goingToLoginPage = to.matched.some(record => record.meta.isLoginPage);

	if (isLoggedIn) {
		await waitUntilTeamLoaded();
		let $team = getTeam();
		let onboardingIncomplete = !$team.doc.payment_mode;
		let onboardingComplete = $team.doc.onboarding.complete;
		let onboardingRoute = $team.doc.onboarding.saas_site_request
			? 'NewAppSite'
			: 'Welcome';
		if (onboardingIncomplete && to.name != onboardingRoute) {
			next({ name: onboardingRoute });
			return;
		}

		if (to.name == onboardingRoute && onboardingComplete) {
			next({ name: 'Home' });
			return;
		}

		if (goingToLoginPage) {
			next({ name: 'Home' });
		} else {
			next();
		}
	} else {
		if (goingToLoginPage) {
			next();
		} else {
			next({ name: 'Login' });
		}
	}
});

function waitUntilTeamLoaded() {
	return new Promise(resolve => {
		let interval = setInterval(() => {
			let team = getTeam();
			if (team?.doc) {
				clearInterval(interval);
				resolve();
			}
		}, 100);
	});
}

export default router;
