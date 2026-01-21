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
			path: '/accept-invite/:requestKey/:joinRequest?',
			name: 'Team Invite',
			component: () => import('./pages/SetupAccount.vue'),
			props: true,
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
			component: () => import('./pages/Checkout.vue'),
			props: true,
			meta: {
				isLoginPage: true,
			},
		},
		{
			path: '/subscription/:site?',
			name: 'Subscription',
			component: () => import('./pages/Subscription.vue'),
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
			name: 'PartnerLeadDetails',
			path: '/partner-lead/:leadId',
			component: () => import('./pages/PartnerLeadDetails.vue'),
			children: [
				{
					name: 'LeadOverview',
					path: '',
					component: () =>
						import('./components/partners/PartnerLeadOverview.vue'),
				},
				{
					name: 'LeadDealDetails',
					path: 'deal-info',
					component: () => import('./components/partners/LeadDealDetails.vue'),
				},
				{
					name: 'LeadFollowUp',
					path: 'follow-up',
					component: () => import('./components/partners/LeadFollowup.vue'),
				},
				{
					name: 'LeadActivities',
					path: 'activities',
					component: () => import('./components/partners/LeadActivities.vue'),
				},
			],
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
					name: 'BillingForecast',
					path: 'forecast',
					component: () => import('./pages/BillingForecast.vue'),
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
				{
					name: 'BillingUPIAutopay',
					path: 'upi-autopay',
					component: () => import('./pages/BillingUPIAutopay.vue'),
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
							path: 'roles/:id',
							component: () => import('./components/settings/Role.vue'),
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
					name: 'PartnerWebsiteDetails',
					path: 'website-details',
					component: () =>
						import('./components/partners/PartnerWebsiteDetails.vue'),
				},
				{
					name: 'PartnerCustomers',
					path: 'customers',
					component: () => import('./components/partners/PartnerCustomers.vue'),
				},
				{
					name: 'PartnerLeads',
					path: 'partner-leads',
					component: () => import('./components/partners/PartnerLeads.vue'),
				},
				{
					name: 'PartnerCertificates',
					path: 'certificates',
					component: () =>
						import('./components/partners/PartnerCertificates.vue'),
				},
				{
					name: 'PartnerResources',
					path: 'resources',
					component: () => import('./components/partners/PartnerResources.vue'),
				},
				{
					name: 'PartnerContributions',
					path: 'contributions',
					component: () =>
						import('./components/partners/PartnerContributionList.vue'),
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
				{
					name: 'PartnerDashboard',
					path: 'partner-dashboard',
					component: () => import('./components/partners/PartnerDashboard.vue'),
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
				{
					name: 'PartnerAdminLeads',
					path: 'partner-admin-lead-list',
					component: () => import('./pages/PartnerAdminLeads.vue'),
				},
				{
					name: 'PartnerAdminResources',
					path: 'admin-resources',
					component: () => import('./components/partners/PartnerResources.vue'),
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
					component: () => import('./pages/signup/AppSelector.vue'),
					meta: { hideSidebar: true },
				},
				{
					name: 'SignupSetup',
					path: ':productId/setup',
					component: () => import('./pages/signup/SetupSite.vue'),
					props: true,
					meta: { hideSidebar: true },
				},
				{
					name: 'SignupLoginToSite',
					path: ':productId/login-to-site',
					component: () => import('./pages/signup/LoginToSite.vue'),
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
			name: 'NewSiteProgress',
			path: '/sites/new/progress/:siteGroupDeployName',
			component: () => import('./pages/NewSiteProgress.vue'),
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
			path: '/enable-bench-groups',
			name: 'Enable Bench Groups',
			component: () => import('./pages/EnableBenchGroups.vue'),
		},
		{
			path: '/enable-servers',
			name: 'Enable Servers',
			component: () => import('./pages/EnableServers.vue'),
		},
		{
			path: '/database-analyzer',
			name: 'DB Analyzer',
			component: () => import('./pages/devtools/database/DatabaseAnalyzer.vue'),
		},
		{
			path: '/binlog-browser',
			name: 'Binlog Browser',
			component: () => import('./pages/devtools/database/BinlogBrowser.vue'),
		},
		{
			path: '/log-browser/:mode?/:docName?/:logId?',
			name: 'Log Browser',
			component: () => import('./pages/devtools/log-browser/LogBrowser.vue'),
			props: true,
		},
		{
			path: '/backups/sites',
			name: 'Site Backups',
			component: () => import('./pages/backups/SiteBackups.vue'),
			props: true,
		},
		{
			path: '/backups/snapshots',
			name: 'Snapshots',
			component: () => import('./pages/backups/ServerSnapshots.vue'),
			props: true,
		},
		...generateRoutes(),
		// TODO: makeshift redirect fixes for /insights paths
		{
			path: '/sites/:site/insights/overview',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/overview`,
			}),
		},
		{
			path: '/sites/:site/insights/apps',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/apps`,
			}),
		},
		{
			path: '/sites/:site/insights/domains',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/domains`,
			}),
		},
		{
			path: '/sites/:site/insights/backups',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/backups`,
			}),
		},
		{
			path: '/sites/:site/insights/site-config',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/site-config`,
			}),
		},
		{
			path: '/sites/:site/insights/actions',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/actions`,
			}),
		},
		{
			path: '/sites/:site/insights/updates',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/updates`,
			}),
		},
		{
			path: '/sites/:site/insights/activity',
			redirect: (to) => ({
				path: `/sites/${to.params.site}/activity`,
			}),
		},
		{
			path: '/:pathMatch(.*)*',
			name: '404',
			component: () => import('./pages/404.vue'),
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

		if (to.name.startsWith('Release Group')) {
			if (!$team.doc.benches_enabled)
				try {
					await $team.setValue.submit({ benches_enabled: 1 });
				} catch (e) {
					console.warn('Auto-enable benches failed:', e);
				}
			if (!onboardingComplete) {
				next({ name: 'Enable Bench Groups' });
				return;
			}
		} else if (to.name === 'Enable Bench Groups' && onboardingComplete) {
			next({ name: 'Release Group List' });
		}

		if (to.name.startsWith('Server')) {
			if (!$team.doc.servers_enabled)
				try {
					await $team.setValue.submit({ servers_enabled: 1 });
				} catch (e) {
					console.warn('Auto-enable servers failed:', e);
				}
			if (!onboardingComplete) {
				next({ name: 'Enable Servers' });
				return;
			}
		} else if (to.name === 'Enable Server' && onboardingComplete) {
			next({ name: 'Server List' });
		}

		if (goingToLoginPage) {
			if (to.name == 'Signup' && to.query?.product) {
				next({
					name: 'SignupSetup',
					params: { productId: to.query.product },
				});
			}
			if (to.name == 'Setup Account') {
				next({ name: 'Team Invite', params: to.params });
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
