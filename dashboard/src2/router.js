import { createRouter, createWebHistory } from 'vue-router';
import { getTeam } from './data/team';
import generateRoutes from './objects/generateRoutes';

let router = createRouter({
	history: createWebHistory('/dashboard/'),
	routes: [
		{
			path: '/',
			name: 'Home',
			component: () => import('./pages/Home.vue'),
			beforeEnter: (to, from, next) => {
				next({
					name: 'Welcome',
					query: {
						is_redirect: true
					}
				});
			}
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
			path: '/checkout/:secretKey',
			name: 'Checkout',
			component: () => import('../src/views/checkout/Checkout.vue'),
			props: true,
			meta: {
				isLoginPage: true
			}
		},
		{
			path: '/in-desk-billing/:accessToken',
			name: 'IntegratedBilling',
			component: () => import('./pages/saas/InDeskBilling.vue'),
			children: [
				{
					path: '',
					redirect: { name: 'IntegratedBillingOverview' }
				},
				{
					path: 'overview',
					name: 'IntegratedBillingOverview',
					component: () => import('./pages/saas/in_desk_billing/Overview.vue')
				},
				{
					path: 'invoices',
					name: 'IntegratedBillingInvoices',
					component: () => import('./pages/saas/in_desk_billing/Invoices.vue')
				}
			],
			props: false,
			meta: {
				isLoginPage: true
			}
		},
		{
			path: '/subscription/:site?',
			name: 'Subscription',
			component: () => import('../src/views/checkout/Subscription.vue'),
			props: true,
			meta: {
				hideSidebar: true
			}
		},
		{
			name: 'Enable2FA',
			path: '/enable-2fa',
			component: () => import('./pages/Enable2FA.vue'),
			props: true,
			meta: {
				hideSidebar: true
			}
		},
		{
			name: 'New Site',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue')
		},
		{
			name: 'Release Group New Site',
			path: '/groups/:bench/sites/new',
			component: () => import('./pages/NewSite.vue'),
			props: true
		},
		{
			name: 'New Release Group',
			path: '/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue')
		},
		{
			name: 'Server New Release Group',
			path: '/servers/:server/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue'),
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
					name: 'SettingsDeveloper',
					path: 'developer',
					component: () => import('./components/settings/DeveloperSettings.vue')
				},
				{
					name: 'SettingsPermission',
					path: 'permissions',
					component: () =>
						import('./components/settings/SettingsPermissions.vue'),
					redirect: { name: 'SettingsPermissionRoles' },
					children: [
						{
							path: 'roles',
							name: 'SettingsPermissionRoles',
							component: () => import('./components/settings/RoleList.vue')
						},
						{
							name: 'SettingsPermissionRolePermissions',
							path: 'roles/:roleId',
							component: () =>
								import('./components/settings/RolePermissions.vue'),
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
			name: 'AppTrial',
			path: '/app-trial',
			redirect: { name: 'Home' },
			children: [
				{
					name: 'AppTrialSignup',
					path: 'signup/:productId',
					component: () => import('./pages/saas/Signup.vue'),
					props: true,
					meta: { isLoginPage: true }
				},
				{
					name: 'AppTrialSetup',
					path: 'setup/:productId',
					component: () => import('./pages/saas/Setup.vue'),
					props: true
				}
			]
		},
		{
			name: 'Impersonate',
			path: '/impersonate/:teamId',
			component: () => import('./pages/Impersonate.vue'),
			props: true
		},
		{
			name: 'InstallApp',
			path: '/install-app/:app',
			component: () => import('./pages/InstallApp.vue'),
			props: true
		},
		{
			name: 'CreateSiteForMarketplaceApp',
			path: '/create-site/:app',
			component: () => import('./pages/CreateSiteForMarketplaceApp.vue'),
			props: true
		},
		{
			path: '/user-review/:marketplaceApp',
			name: 'ReviewMarketplaceApp',
			component: () =>
				import('./components/marketplace/ReviewMarketplaceApp.vue'),
			props: true
		},
		{
			path: '/developer-reply/:marketplaceApp/:reviewId',
			name: 'ReplyMarketplaceApp',
			component: () =>
				import('./components/marketplace/ReplyMarketplaceApp.vue'),
			props: true
		},
		{
			path: '/sql-playground',
			name: 'SQL Playground',
			component: () =>
				import('./pages/devtools/database/DatabaseSQLPlayground.vue')
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
		!document.cookie.includes('user_id=Guest');
	let goingToLoginPage = to.matched.some(record => record.meta.isLoginPage);

	if (to.name.startsWith('IntegratedBilling')) {
		next();
		return;
	}

	if (isLoggedIn) {
		await waitUntilTeamLoaded();
		let $team = getTeam();
		let onboardingComplete = $team.doc.onboarding.complete;
		let defaultRoute = 'Site List';
		let onboardingRoute = 'Welcome';

		// identify user in posthog
		if (window.posthog?.__loaded) {
			try {
				window.posthog.identify($team.doc.user, {
					app: 'frappe_cloud'
				});
			} catch (e) {
				console.error(e);
			}
		}

		// If user is logged in and was moving to app trial signup, redirect to app trial setup
		if (to.name == 'AppTrialSignup') {
			next({ name: 'AppTrialSetup', params: to.params });
			return;
		}

		// if team owner/admin enforce 2fa and user has not enabled 2fa, redirect to enable 2fa
		const Enable2FARoute = 'Enable2FA';
		if (
			to.name !== Enable2FARoute &&
			!$team.doc.is_desk_user &&
			$team.doc.enforce_2fa &&
			!$team.doc.user_info.is_2fa_enabled
		) {
			next({ name: Enable2FARoute });
			return;
		}

		// if team owner/admin doesn't enforce 2fa don't allow user to visit Enable2FA route
		if (to.name === Enable2FARoute && !$team.doc.enforce_2fa) {
			next({ name: defaultRoute });
			return;
		}

		if (
			!onboardingComplete &&
			(to.name.startsWith('Release Group') || to.name.startsWith('Server'))
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
			if (to.name == 'AppTrialSetup') {
				next({
					name: 'AppTrialSignup',
					params: to.params
				});
			} else {
				next({ name: 'Login' });
			}
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
