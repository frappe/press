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
						is_redirect: true,
					},
				});
			},
		},
		{
			path: '/welcome',
			name: 'Welcome',
			component: () => import('./pages/Welcome.vue'),
			meta: { hideSidebar: true },
		},
		{
			path: '/login',
			name: 'Login',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true },
		},
		{
			path: '/signup',
			name: 'Signup',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true },
		},
		{
			path: '/site-login',
			name: 'Site Login',
			component: () => import('./pages/SiteLogin.vue'),
			meta: { hideSidebar: true },
		},
		{
			path: '/setup-account/:requestKey/:joinRequest?',
			name: 'Setup Account',
			component: () => import('./pages/SetupAccount.vue'),
			props: true,
			meta: { isLoginPage: true },
		},
		{
			path: '/reset-password/:requestKey',
			name: 'Reset Password',
			component: () => import('./pages/ResetPassword.vue'),
			props: true,
			meta: { isLoginPage: true },
		},
		{
			path: '/checkout/:secretKey',
			name: 'Checkout',
			component: () => import('../src/views/checkout/Checkout.vue'),
			props: true,
			meta: {
				isLoginPage: true,
			},
		},
		{
			path: '/subscription/:site?',
			name: 'Subscription',
			component: () => import('../src/views/checkout/Subscription.vue'),
			props: true,
			meta: {
				hideSidebar: true,
			},
		},
		{
			name: 'Enable2FA',
			path: '/enable-2fa',
			component: () => import('./pages/Enable2FA.vue'),
			props: true,
			meta: {
				hideSidebar: true,
			},
		},
		{
			name: 'New Site',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue'),
		},
		{
			name: 'Release Group New Site',
			path: '/groups/:bench/sites/new',
			component: () => import('./pages/NewSite.vue'),
			props: true,
		},
		{
			name: 'New Release Group',
			path: '/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue'),
		},
		{
			name: 'Server New Release Group',
			path: '/servers/:server/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue'),
			props: true,
		},
		{
			name: 'New Server',
			path: '/servers/new',
			component: () => import('./pages/NewServer.vue'),
		},
		{
			name: 'PartnerNewPayout',
			path: '/payment-payout/New',
			component: () => import('./pages/PartnerNewPayout.vue'),
		},
		{
			name: 'Billing',
			path: '/billing',
			component: () => import('./pages/Billing.vue'),
			children: [
				{
					name: 'BillingOverview',
					path: '',
					component: () => import('./pages/BillingOverview.vue'),
				},
				{
					name: 'BillingInvoices',
					path: 'invoices',
					component: () => import('./pages/BillingInvoices.vue'),
				},
				{
					name: 'BillingBalances',
					path: 'balances',
					component: () => import('./pages/BillingBalances.vue'),
				},
				{
					name: 'BillingPaymentMethods',
					path: 'payment-methods',
					component: () => import('./pages/BillingPaymentMethods.vue'),
				},
				{
					name: 'BillingMarketplacePayouts',
					path: 'payouts',
					component: () => import('./pages/BillingMarketplacePayouts.vue'),
				},
				{
					name: 'BillingMpesaInvoices',
					path: 'mpesa-invoices',
					component: () => import('./pages/BillingMpesaInvoices.vue'),
				},
			],
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
						import('./components/settings/profile/ProfileSettings.vue'),
				},
				{
					name: 'SettingsTeam',
					path: 'team',
					component: () => import('./components/settings/TeamSettings.vue'),
				},
				{
					name: 'SettingsDeveloper',
					path: 'developer',
					component: () =>
						import('./components/settings/DeveloperSettings.vue'),
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
							component: () => import('./components/settings/RoleList.vue'),
						},
						{
							name: 'SettingsPermissionRolePermissions',
							path: 'roles/:roleId',
							component: () =>
								import('./components/settings/RolePermissions.vue'),
							props: true,
						},
					],
				},
			],
		},
		{
			name: 'Partnership',
			path: '/partners',
			redirect: { name: 'PartnerOverview' },
			component: () => import('./pages/Partners.vue'),
			children: [
				{
					name: 'PartnerOverview',
					path: 'overview',
					component: () => import('./components/partners/PartnerOverview.vue'),
				},
				{
					name: 'PartnerCustomers',
					path: 'customers',
					component: () => import('./components/partners/PartnerCustomers.vue'),
				},
				{
					name: 'PartnerCertificates',
					path: 'certificates',
					component: () =>
						import('./components/partners/PartnerCertificates.vue'),
				},
				{
					name: 'PartnerApprovalRequests',
					path: 'approval-requests',
					component: () =>
						import('./components/partners/PartnerApprovalRequests.vue'),
				},
				{
					name: 'LocalPaymentSetup',
					path: 'local-payment-setup',
					component: () =>
						import('./components/partners/PartnerLocalPaymentSetup.vue'),
				},
				{
					name: 'PartnerPayout',
					path: 'payment-payout',
					component: () => import('./components/partners/PartnerPayout.vue'),
				},
			],
		},
		{
			name: 'Partner Admin',
			path: '/partner-admin',
			redirect: { name: 'PartnerList' },
			component: () => import('./pages/PartnerAdmin.vue'),
			children: [
				{
					name: 'PartnerList',
					path: 'partner-list',
					component: () => import('./pages/PartnerList.vue'),
				},
				{
					name: 'CertificateList',
					path: 'certificate-list',
					component: () => import('./pages/PartnerAdminCertificates.vue'),
				},
			],
		},
		{
			name: 'Signup Create Site',
			path: '/create-site',
			redirect: { name: 'Home' },
			children: [
				{
					name: 'SignupAppSelector',
					path: 'app-selector',
					component: () => import('./pages/saas/AppSelector.vue'),
					meta: { hideSidebar: true },
				},
				{
					name: 'SignupSetup',
					path: ':productId/setup',
					component: () => import('./pages/saas/SetupSite.vue'),
					props: true,
					meta: { hideSidebar: true },
				},
				{
					name: 'SignupLoginToSite',
					path: ':productId/login-to-site',
					component: () => import('./pages/saas/LoginToSite.vue'),
					props: true,
					meta: { hideSidebar: true },
				},
			],
		},
		{
			name: 'Impersonate',
			path: '/impersonate/:teamId',
			component: () => import('./pages/Impersonate.vue'),
			props: true,
		},
		{
			name: 'InstallApp',
			path: '/install-app/:app',
			component: () => import('./pages/InstallApp.vue'),
			props: true,
		},
		{
			name: 'CreateSiteForMarketplaceApp',
			path: '/create-site/:app',
			component: () => import('./pages/CreateSiteForMarketplaceApp.vue'),
			props: true,
		},
		{
			path: '/developer-reply/:marketplaceApp/:reviewId',
			name: 'ReplyMarketplaceApp',
			component: () =>
				import('./components/marketplace/ReplyMarketplaceApp.vue'),
			props: true,
		},
		{
			path: '/sql-playground',
			name: 'SQL Playground',
			component: () =>
				import('./pages/devtools/database/DatabaseSQLPlayground.vue'),
		},
		{
			path: '/database-analyzer',
			name: 'DB Analyzer',
			component: () => import('./pages/devtools/database/DatabaseAnalyzer.vue'),
		},
		{
			path: '/log-browser/:mode?/:docName?/:logId?',
			name: 'Log Browser',
			component: () => import('./pages/devtools/log-browser/LogBrowser.vue'),
			props: true,
		},
		...generateRoutes(),
		{
			path: '/:pathMatch(.*)*',
			name: '404',
			component: () => import('../src/views/general/404.vue'),
		},
	],
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn =
		document.cookie.includes('user_id') &&
		!document.cookie.includes('user_id=Guest');
	let goingToLoginPage = to.matched.some((record) => record.meta.isLoginPage);

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
					app: 'frappe_cloud',
				});
			} catch (e) {
				console.error(e);
			}
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
			if (to.name == 'Signup' && to.query?.product) {
				next({
					name: 'SignupSetup',
					params: { productId: to.query.product },
				});
			}
			next({ name: defaultRoute });
		} else {
			next();
		}
	} else {
		if (goingToLoginPage) {
			next();
		} else {
			if (to.name == 'Site Login') {
				next();
			} else {
				next({ name: 'Login', query: { redirect: to.href } });
			}
		}
	}
});

function waitUntilTeamLoaded() {
	return new Promise((resolve) => {
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
