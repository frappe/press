import { createRouter, createWebHistory } from 'vue-router';
import { getTeam } from './data/team';
import generateRoutes from './objects/generateRoutes';

let router = createRouter({
	history: createWebHistory('/dashboard-beta/'),
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
			name: 'New Site',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue')
		},
		{
			name: 'Bench New Site',
			path: '/benches/:bench/sites/new',
			component: () => import('./pages/NewSite.vue'),
			props: true
		},
		{
			name: 'New Release Group',
			path: '/benches/new',
			component: () => import('./pages/NewBench.vue')
		},
		{
			name: 'Server New Bench',
			path: '/servers/:server/benches/new',
			component: () => import('./pages/NewBench.vue'),
			props: true
		},
		{
			name: 'New Server',
			path: '/servers/new',
			component: () => import('./pages/NewServer.vue')
		},
		{
			name: 'Billing',
			path: '/billing',
			component: () => import('./pages/Billing.vue'),
			children: [
				{
					name: 'BillingOverview',
					path: '',
					component: () => import('./pages/BillingOverview.vue')
				},
				{
					name: 'BillingInvoices',
					path: 'invoices',
					component: () => import('./pages/BillingInvoices.vue')
				},
				{
					name: 'BillingBalances',
					path: 'balances',
					component: () => import('./pages/BillingBalances.vue')
				},
				{
					name: 'BillingPaymentMethods',
					path: 'payment-methods',
					component: () => import('./pages/BillingPaymentMethods.vue')
				},
				{
					name: 'BillingMarketplacePayouts',
					path: 'payouts',
					component: () => import('./pages/BillingMarketplacePayouts.vue')
				}
			]
		},
		{
			path: '/settings',
			name: 'Settings',
			redirect: { name: 'SettingsProfile' },
			component: () => import('./pages/Settings.vue'),
			children: [
				{
					name: 'SettingsProfile',
					path: 'profile',
					component: () =>
						import('./components/settings/profile/ProfileSettings.vue')
				},
				{
					name: 'SettingsTeam',
					path: 'team',
					component: () => import('./components/settings/TeamSettings.vue')
				},
				{
					name: 'SettingsPermission',
					path: 'permissions',
					component: () =>
						import('./components/settings/PermissionsSettings.vue'),
					redirect: { name: 'SettingsPermissionGroupList' },
					children: [
						{
							path: 'groups',
							name: 'SettingsPermissionGroupList',
							component: () =>
								import('./components/settings/PermissionGroupList.vue')
						},
						{
							name: 'SettingsPermissionGroupPermissions',
							path: 'groups/:groupId',
							component: () =>
								import('./components/settings/PermissionGroupPermissions.vue'),
							props: true
						}
					]
				}
			]
		},
		{
			name: 'Partners',
			path: '/partners',
			redirect: { name: 'PartnerOverview' },
			component: () => import('./pages/Partners.vue'),
			children: [
				{
					name: 'PartnerOverview',
					path: 'overview',
					component: () => import('./components/partners/PartnerOverview.vue')
				},
				{
					name: 'PartnerCustomers',
					path: 'customers',
					component: () => import('./components/partners/PartnerCustomers.vue')
				},
				{
					name: 'PartnerApprovalRequests',
					path: 'approval-requests',
					component: () =>
						import('./components/partners/PartnerApprovalRequests.vue')
				}
			]
		},
		{
			name: 'NewAppTrial',
			path: '/app-trial/:productId',
			component: () => import('./pages/NewAppTrial.vue'),
			props: true
		},
		{
			name: 'Impersonate',
			path: '/impersonate/:teamId',
			component: () => import('./pages/Impersonate.vue'),
			props: true
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
		let onboardingComplete = $team.doc.onboarding.complete;
		let onboardingIncomplete = !onboardingComplete;
		let defaultRoute = 'Site List';
		let onboardingRoute = 'Welcome';

		let visitingSiteOrBillingOrSettings =
			to.name.startsWith('Site') ||
			to.name.startsWith('Billing') ||
			to.name.startsWith('Settings');

		// if onboarding is incomplete, only allow access to Welcome, Site, Billing, and Settings pages
		if (
			onboardingIncomplete &&
			to.name != onboardingRoute &&
			!visitingSiteOrBillingOrSettings
		) {
			next({ name: onboardingRoute });
			return;
		}

		if (goingToLoginPage) {
			next({ name: defaultRoute });
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
