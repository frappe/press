import { createRouter, createWebHistory } from 'vue-router'
import session from './data/session'
import { getTeam } from './data/team'
import generateRoutes from './objects/generateRoutes'
import { routeTitle } from './utils/title'

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
						...to.query,
						is_redirect: true,
					},
				})
			},
		},
		{
			path: '/welcome',
			name: 'Welcome',
			component: () => import('./pages/Welcome.vue'),
			meta: { hideSidebar: true, title: 'Welcome' },
		},
		{
			path: '/quickstart',
			name: 'Quickstart',
			component: () => import('./pages/Quickstart.vue'),
			meta: { hideSidebar: true, title: 'Quickstart' },
		},
		{
			path: '/login',
			name: 'Login',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true, title: 'Login' },
		},
		{
			path: '/signup',
			name: 'Signup',
			component: () => import('./pages/LoginSignup.vue'),
			meta: { isLoginPage: true, title: 'Sign Up' },
		},
		{
			path: '/site-login',
			name: 'Site Login',
			component: () => import('./pages/SiteLogin.vue'),
			meta: { hideSidebar: true, title: 'Site Login' },
		},
		{
			path: '/setup-account/:requestKey/:joinRequest?',
			name: 'Setup Account',
			component: () => import('./pages/SetupAccount.vue'),
			props: true,
			meta: { isLoginPage: true, title: 'Setup Account' },
		},
		{
			path: '/accept-invite/:requestKey/:joinRequest?',
			name: 'Team Invite',
			component: () => import('./pages/SetupAccount.vue'),
			props: true,
			meta: { title: 'Team Invite' },
		},
		{
			path: '/reset-password/:requestKey',
			name: 'Reset Password',
			component: () => import('./pages/ResetPassword.vue'),
			props: true,
			meta: { isLoginPage: true, title: 'Reset Password' },
		},
		{
			path: '/checkout/:secretKey',
			name: 'Checkout',
			component: () => import('./pages/Checkout.vue'),
			props: true,
			meta: {
				isLoginPage: true,
				title: 'Checkout',
			},
		},
		{
			path: '/subscription/:site?',
			name: 'Subscription',
			component: () => import('./pages/Subscription.vue'),
			props: true,
			meta: {
				hideSidebar: true,
				title: 'Manage Subscription',
			},
		},
		{
			name: 'Enable2FA',
			path: '/enable-2fa',
			component: () => import('./pages/Enable2FA.vue'),
			props: true,
			meta: {
				hideSidebar: true,
				title: 'Enable 2FA',
			},
		},
		{
			name: 'New Site',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue'),
			meta: { title: 'New Site' },
		},
		{
			name: 'Release Group New Site',
			path: '/groups/:bench/sites/new',
			component: () => import('./pages/NewSite.vue'),
			props: true,
			meta: { title: 'New Site' },
		},

		{
			name: 'Server New Site',
			path: '/servers/:server/sites/new',
			component: () => import('./pages/NewSite.vue'),
			props: true,
			meta: { title: 'New Site' },
		},
		{
			name: 'New Release Group',
			path: '/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue'),
			meta: { title: 'New Bench' },
		},
		{
			name: 'Server New Release Group',
			path: '/servers/:server/groups/new',
			component: () => import('./pages/NewReleaseGroup.vue'),
			props: true,
			meta: { title: 'New Bench' },
		},
		{
			name: 'New Server',
			path: '/servers/new',
			component: () => import('./pages/NewServer.vue'),
			meta: { title: 'New Server' },
		},
		{
			name: 'PartnerNewPayout',
			path: '/payment-payout/New',
			component: () => import('./pages/PartnerNewPayout.vue'),
			meta: { title: 'New Payout' },
		},
		{
			name: 'PartnerLeadDetails',
			path: '/partner-lead/:leadId',
			component: () => import('./pages/PartnerLeadDetails.vue'),
			meta: { title: (route) => route.params.leadId },
			children: [
				{
					name: 'LeadOverview',
					path: '',
					component: () =>
						import('./components/partners/PartnerLeadOverview.vue'),
					meta: { title: 'Overview' },
				},
				{
					name: 'LeadDealDetails',
					path: 'deal-info',
					component: () => import('./components/partners/LeadDealDetails.vue'),
					meta: { title: 'Follow-up' },
				},
				{
					name: 'LeadFollowUp',
					path: 'follow-up',
					component: () => import('./components/partners/LeadFollowup.vue'),
					meta: { title: 'Follow-up' },
				},
				{
					name: 'LeadActivities',
					path: 'activities',
					component: () => import('./components/partners/LeadActivities.vue'),
					meta: { title: 'Activities' },
				},
			],
		},
		{
			name: 'Billing',
			path: '/billing',
			component: () => import('./pages/Billing.vue'),
			meta: { title: 'Billing' },
			children: [
				{
					name: 'BillingOverview',
					path: '',
					component: () => import('./pages/BillingOverview.vue'),
					meta: { title: 'Overview' },
				},
				{
					name: 'BillingForecast',
					path: 'forecast',
					component: () => import('./pages/BillingForecast.vue'),
					meta: { title: 'Forecast' },
				},
				{
					name: 'BillingInvoices',
					path: 'invoices',
					component: () => import('./pages/BillingInvoices.vue'),
					meta: { title: 'Invoices' },
				},
				{
					name: 'BillingBalances',
					path: 'balances',
					component: () => import('./pages/BillingBalances.vue'),
					meta: { title: 'Balances' },
				},
				{
					name: 'BillingPaymentMethods',
					path: 'payment-methods',
					component: () => import('./pages/BillingPaymentMethods.vue'),
					meta: { title: 'Payment Methods' },
				},
				{
					name: 'BillingMarketplacePayouts',
					path: 'payouts',
					component: () => import('./pages/BillingMarketplacePayouts.vue'),
					meta: { title: 'Marketplace Payouts' },
				},
				{
					name: 'BillingSubscriptions',
					path: 'subscriptions',
					component: () => import('./pages/BillingSubscriptions.vue'),
					meta: { title: 'Subscriptions' },
				},
				{
					name: 'BillingTiers',
					path: 'tiers',
					component: () => import('./pages/BillingTiers.vue'),
					meta: { title: 'Limits' },
				},
				{
					name: 'BillingMpesaInvoices',
					path: 'mpesa-invoices',
					component: () => import('./pages/BillingMpesaInvoices.vue'),
					meta: { title: 'Mpesa Invoices' },
				},
				{
					name: 'BillingUPIAutopay',
					path: 'upi-autopay',
					component: () => import('./pages/BillingUPIAutopay.vue'),
					meta: { title: 'UPI Autopay' },
				},
			],
		},
		{
			path: '/settings',
			name: 'Settings',
			redirect: { name: 'SettingsProfile' },
			component: () => import('./pages/Settings.vue'),
			meta: { title: 'Settings' },
			children: [
				{
					name: 'SettingsProfile',
					path: 'profile',
					component: () =>
						import('./components/settings/profile/ProfileSettings.vue'),
					meta: { title: 'Profile' },
				},
				{
					name: 'SettingsTeam',
					path: 'team',
					component: () => import('./components/settings/TeamSettings.vue'),
					meta: { title: 'Team' },
				},
				{
					name: 'SettingsDeveloper',
					path: 'developer',
					component: () =>
						import('./components/settings/DeveloperSettings.vue'),
					meta: { title: 'Developer' },
				},
				{
					name: 'SettingsPermission',
					path: 'permissions',
					component: () =>
						import('./components/settings/SettingsPermissions.vue'),
					redirect: { name: 'SettingsPermissionRoles' },
					meta: { title: 'Roles' },
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

				{
					name: 'SettingsPartnerAdmin',
					path: 'partner-admin',
					redirect: { name: 'PartnerList' },
					component: () => import('./pages/PartnerAdmin.vue'),
					meta: { title: 'Partner Admin' },
					children: [
						{
							name: 'PartnerList',
							path: 'partner-list',
							component: () => import('./pages/PartnerList.vue'),
							meta: { title: 'Partner List' },
						},
						{
							name: 'CertificateList',
							path: 'certificate-list',
							component: () => import('./pages/PartnerAdminCertificates.vue'),
							meta: { title: 'Certificates' },
						},
						{
							name: 'PartnerAdminLeads',
							path: 'partner-admin-lead-list',
							component: () => import('./pages/PartnerAdminLeads.vue'),
							meta: { title: 'Leads' },
						},
						{
							name: 'PartnerAdminResources',
							path: 'admin-resources',
							component: () =>
								import('./components/partners/PartnerResources.vue'),
							meta: { title: 'Resources' },
						},
						{
							name: 'PartnerAdminAudits',
							path: 'admin-audits',
							component: () =>
								import('./components/partners/PartnerAdminAudits.vue'),
							meta: { title: 'Audits' },
						},
					],
				},
			],
		},
		{
			name: 'Status Page',
			path: '/status',
			component: () => import('./pages/PrivateStatusPage.vue'),
			redirect: { name: 'OngoingIncidents' },
			meta: { title: 'Status' },
			children: [
				{
					name: 'OngoingIncidents',
					path: 'ongoing-incidents',
					component: () => import('./components/status/PrivateIncident.vue'),
					meta: { title: 'Ongoing Incidents' },
				},
				{
					name: 'IncidentHistory',
					path: 'incident-history',
					component: () => import('./components/status/PrivateIncident.vue'),
					meta: { title: 'Incident History' },
				},
			],
		},
		{
			name: 'Partnership',
			path: '/partners',
			redirect: { name: 'PartnerOverview' },
			component: () => import('./pages/Partners.vue'),
			meta: { title: 'Partnership' },
			children: [
				{
					name: 'PartnerOverview',
					path: 'overview',
					component: () => import('./components/partners/PartnerOverview.vue'),
					meta: { title: 'Overview' },
				},
				{
					name: 'PartnerWebsiteDetails',
					path: 'website-details',
					component: () =>
						import('./components/partners/PartnerWebsiteDetails.vue'),
					meta: { title: 'Website Details' },
				},
				{
					name: 'PartnerCustomers',
					path: 'customers',
					component: () => import('./components/partners/PartnerCustomers.vue'),
					meta: { title: 'Customers' },
				},
				{
					name: 'PartnerLeads',
					path: 'partner-leads',
					component: () => import('./components/partners/PartnerLeads.vue'),
					meta: { title: 'Leads' },
				},
				{
					name: 'PartnerCertificates',
					path: 'certificates',
					component: () =>
						import('./components/partners/PartnerCertificates.vue'),
					meta: { title: 'Certifications' },
				},
				{
					name: 'PartnerResources',
					path: 'resources',
					component: () => import('./components/partners/PartnerResources.vue'),
					meta: { title: 'Resources' },
				},
				{
					name: 'PartnerContributions',
					path: 'contributions',
					component: () =>
						import('./components/partners/PartnerContributionList.vue'),
					meta: { title: 'Contributions' },
				},
				{
					name: 'PartnerAudits',
					path: 'audits',
					component: () => import('./components/partners/PartnerAudits.vue'),
					meta: { title: 'Audits' },
				},
				{
					name: 'PartnerNCList',
					path: 'audit/:partner_audit?',
					component: () => import('./components/partners/PartnerNCList.vue'),
					props: true,
					meta: { title: 'Audit' },
					children: [
						{
							name: 'PartnerNCSummary',
							path: 'nc-summary/:nc?',
							props: true,
							meta: { title: 'Non-conformance Summary' },
							component: () =>
								import('./components/partners/PartnerNCSummary.vue'),
						},
					],
				},
				{
					name: 'LocalPaymentSetup',
					path: 'local-payment-setup',
					component: () =>
						import('./components/partners/PartnerLocalPaymentSetup.vue'),
					meta: { title: 'Local Payment Setup' },
				},
				{
					name: 'PartnerPayout',
					path: 'payment-payout',
					component: () => import('./components/partners/PartnerPayout.vue'),
					meta: { title: 'Partner Payout' },
				},
				{
					name: 'PartnerDashboard',
					path: 'partner-dashboard',
					component: () => import('./components/partners/PartnerDashboard.vue'),
					meta: { title: 'Dashboard' },
				},
			],
		},
		{
			name: 'Partner Onboarding',
			path: '/partner-onboarding',
			component: () => import('@/onboarding/PartnerOnboarding.vue'),
			meta: { title: 'Partner Onboarding' },
		},
		{
			name: 'Signup Create Site',
			path: '/create-site',
			redirect: { name: 'Home' },
			meta: { title: 'Create Site' },
			children: [
				{
					name: 'SignupAppSelector',
					path: 'app-selector',
					component: () => import('./pages/signup/AppSelector.vue'),
					meta: { hideSidebar: true, title: 'Select App' },
				},
				{
					name: 'SignupSetup',
					path: ':productId/setup',
					component: () => import('./pages/signup/SetupSite.vue'),
					props: true,
					meta: { hideSidebar: true, title: 'Set Up Site' },
				},
				{
					name: 'SignupLoginToSite',
					path: ':productId/login-to-site',
					component: () => import('./pages/signup/LoginToSite.vue'),
					props: true,
					meta: { hideSidebar: true, title: 'Log In To Site' },
				},
			],
		},
		{
			name: 'Impersonate',
			path: '/impersonate/:teamId',
			component: () => import('./pages/Impersonate.vue'),
			props: true,
			meta: { title: 'Impersonate' },
		},
		{
			name: 'InstallApp',
			path: '/install-app/:app',
			component: () => import('./pages/InstallApp.vue'),
			props: true,
			meta: { title: 'Install App' },
		},
		{
			name: 'CreateSiteForMarketplaceApp',
			path: '/create-site/:app',
			component: () => import('./pages/CreateSiteForMarketplaceApp.vue'),
			props: true,
			meta: { title: 'Create Site' },
		},
		{
			name: 'NewSiteProgress',
			path: '/sites/new/progress/:siteGroupDeployName',
			component: () => import('./pages/NewSiteProgress.vue'),
			props: true,
			meta: { title: 'New Site' },
		},
		{
			path: '/developer-reply/:marketplaceApp/:reviewId',
			name: 'ReplyMarketplaceApp',
			component: () =>
				import('./components/marketplace/ReplyMarketplaceApp.vue'),
			props: true,
			meta: { title: 'Reply to Review' },
		},
		{
			path: '/sql-playground',
			name: 'SQL Playground',
			component: () =>
				import('./pages/devtools/database/DatabaseSQLPlayground.vue'),
			meta: { title: 'SQL Playground' },
		},
		{
			path: '/enable-bench-groups',
			name: 'Enable Benches',
			component: () => import('./pages/EnableBenchGroups.vue'),
			meta: { title: 'Enable Benches' },
		},
		{
			path: '/enable-servers',
			name: 'Enable Servers',
			component: () => import('./pages/EnableServers.vue'),
			meta: { title: 'Enable Servers' },
		},
		{
			path: '/database-analyzer',
			name: 'DB Analyzer',
			component: () => import('./pages/devtools/database/DatabaseAnalyzer.vue'),
			meta: { title: 'Database Analyzer' },
		},
		{
			path: '/binlog-browser',
			name: 'Binlog Browser',
			component: () => import('./pages/devtools/database/BinlogBrowser.vue'),
			meta: { title: 'Binlog Browser' },
		},
		{
			path: '/log-browser/:mode?/:docName?/:logId?',
			name: 'Log Browser',
			component: () => import('./pages/devtools/log-browser/LogBrowser.vue'),
			props: true,
			meta: { title: 'Log Browser' },
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
			meta: { title: 'Page Not Found' },
		},
	],
})

// Pages that load a document refine this in their own pageMeta()
router.afterEach((to) => {
	document.title = routeTitle(to)
})

router.beforeEach(async (to, from, next) => {
	let isLoggedIn =
		document.cookie.includes('user_id') &&
		!document.cookie.includes('user_id=Guest')

	let hasTeamPrivileges = !!window.default_team
	let goingToLoginPage = to.matched.some((record) => record.meta.isLoginPage)

	if (isLoggedIn && window.account_disabled) {
		next(goingToLoginPage ? undefined : { name: 'Login' })
		return
	}

	if (isLoggedIn && hasTeamPrivileges) {
		await waitUntilTeamLoaded()
		let $team = getTeam()
		let onboardingComplete = $team.doc.onboarding.complete
		let defaultRoute = 'Site List'

		// identify user in posthog
		if (window.posthog?.__loaded) {
			try {
				window.posthog.identify($team.doc.user, {
					app: 'frappe_cloud',
				})
			} catch (e) {
				console.error(e)
			}
		}

		// if team owner/admin enforce 2fa and user has not enabled 2fa, redirect to enable 2fa
		const Enable2FARoute = 'Enable2FA'
		if (
			to.name !== Enable2FARoute &&
			!$team.doc.is_desk_user &&
			$team.doc.enforce_2fa &&
			!$team.doc.user_info.is_2fa_enabled
		) {
			next({ name: Enable2FARoute })
			return
		}

		// if team owner/admin doesn't enforce 2fa don't allow user to visit Enable2FA route
		if (to.name === Enable2FARoute && !$team.doc.enforce_2fa) {
			next({ name: defaultRoute })
			return
		}

		// if team is not a partner and trying to access partner routes, redirect to partner onboarding
		const activePartner = Boolean(
			$team.doc.erpnext_partner && $team.doc.partner_status === 'Active',
		)
		const goingToPartnerDashboard = to.matched.some(
			(record) => record.name === 'Partnership',
		)

		if (to.name === 'Partner Onboarding' && activePartner) {
			next({ name: 'PartnerOverview' })
			return
		}

		if (goingToPartnerDashboard && !activePartner) {
			next({ name: 'Partner Onboarding' })
			return
		}

		if (to.name.startsWith('Release Group')) {
			if (!$team.doc.benches_enabled)
				try {
					await $team.setValue.submit({ benches_enabled: 1 })
				} catch (e) {
					console.warn('Auto-enable benches failed:', e)
				}
			if (!onboardingComplete) {
				next({ name: 'Enable Benches' })
				return
			}
		} else if (to.name === 'Enable Benches' && onboardingComplete) {
			next({ name: 'Release Group List' })
		}

		if (to.name.startsWith('Server')) {
			if (!$team.doc.servers_enabled)
				try {
					await $team.setValue.submit({ servers_enabled: 1 })
				} catch (e) {
					console.warn('Auto-enable servers failed:', e)
				}
			if (!onboardingComplete) {
				next({ name: 'Enable Servers' })
				return
			}
		} else if (to.name === 'Enable Server' && onboardingComplete) {
			next({ name: 'Server List' })
		}

		if (goingToLoginPage) {
			if (to.name == 'Signup' && to.query?.product) {
				next({
					name: 'Quickstart',
					query: { product: to.query.product },
				})
				return
			}
			if (to.name == 'Setup Account') {
				next({ name: 'Team Invite', params: to.params })
				return
			}
			next({ name: defaultRoute })
		} else {
			next()
		}
	} else {
		if (goingToLoginPage) {
			next()
		} else {
			if (to.name == 'Site Login') {
				next()
			} else if (!hasTeamPrivileges) {
				logoutWithTeamError()
			} else {
				next({ name: 'Login', query: { redirect: to.href } })
			}
		}
	}
})

function waitUntilTeamLoaded() {
	return new Promise((resolve) => {
		let interval = setInterval(() => {
			let team = getTeam()
			if (team?.doc) {
				clearInterval(interval)
				resolve()
			} else if (team?.get?.error) {
				if (team?.get?.error?.exc_type === 'ValidationError') {
					clearInterval(interval)
					logoutWithTeamError()
				}
			}
		}, 100)
	})
}

function logoutWithTeamError() {
	session.logout.submit()
	router.push({ name: 'Login', query: { reason: 'INVALID_TEAM' } })
}

export default router
