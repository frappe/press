import Home from '../views/general/Home.vue';

import { createRouter, createWebHistory } from 'vue-router';

const routes = [
	{
		path: '/',
		name: 'Home',
		component: Home
	},
	{
		path: '/checkout',
		name: 'Checkout',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/checkout/Checkout.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/login/:forgot?',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/auth/Login.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/signup',
		name: 'Signup',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/auth/Signup.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/setup-account/:requestKey/:joinRequest?',
		name: 'Setup Account',
		component: () =>
			import(
				/* webpackChunkName: "setup-account" */ '../views/auth/SetupAccount.vue'
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
				/* webpackChunkName: "reset-password" */ '../views/auth/ResetPassword.vue'
			),
		props: true,
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/impersonate/:team',
		name: 'Impersonate Team',
		component: () => import('../views/auth/ImpersonateTeam.vue'),
		props: true
	},
	{
		path: '/benches',
		name: 'BenchesScreen',
		component: () => import('../views/bench/Benches.vue')
	},
	{
		path: '/benches/new/:saas_app?',
		name: 'NewBench',
		meta: {
			isSaasPage: true
		},
		component: () => import('../views/bench/NewBench.vue'),
		props: true
	},
	{
		path: '/servers/:server/bench/new',
		name: 'NewServerBench',
		component: () => import('../views/bench/NewBench.vue'),
		props: true
	},
	{
		path: '/benches/:benchName',
		name: 'Bench',
		component: () => import('../views/bench/Bench.vue'),
		props: true,
		meta: {
			isSaasPage: true
		},
		children: [
			{
				path: 'sites',
				component: () => import('../views/bench/BenchSites.vue'),
				props: true
			},
			{
				name: 'BenchOverview',
				path: 'overview',
				component: () => import('../views/bench/BenchOverview.vue')
			},
			{
				path: 'apps',
				component: () => import('../views/bench/BenchApps.vue'),
				props: true
			},
			{
				path: 'versions/:version?',
				component: () => import('../views/bench/BenchVersions.vue'),
				props: true
			},
			{
				path: 'bench-config',
				component: () => import('../views/bench/BenchConfig.vue'),
				props: true
			},
			{
				path: 'deploys/:candidateName?',
				component: () => import('../views/bench/BenchDeploys.vue'),
				props: true
			},
			{
				path: 'logs/:instanceName/:logName?',
				component: () => import('../views/bench/BenchLogs.vue'),
				props: true
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/bench/BenchJobs.vue'),
				props: true
			},
			{
				path: 'setting',
				component: () => import('../views/bench/BenchSettings.vue'),
				props: true
			}
		]
	},
	{
		path: '/benches/:benchName/apps/new',
		name: 'NewBenchApp',
		component: () => import('../views/bench/NewBenchApp.vue'),
		props: true
	},
	{
		path: '/sites',
		name: 'Sites',
		component: () => import('../views/site/Sites.vue')
	},
	{
		path: '/:bench/sites',
		name: 'BenchSites',
		component: () => import('../views/site/Sites.vue'),
		props: true
	},
	{
		path: '/sites/new',
		name: 'NewSite',
		component: () => import('../views/site/NewSite.vue'),
		props: true
	},
	{
		path: '/:bench/new',
		name: 'NewBenchSite',
		component: () => import('../views/site/NewSite.vue'),
		props: true
	},
	{
		path: '/sites/:siteName',
		name: 'Site',
		component: () => import('../views/site/Site.vue'),
		props: true,
		children: [
			{
				name: 'SiteOverview',
				path: 'overview',
				component: () => import('../views/site/SiteOverview.vue')
			},
			{
				name: 'SiteOverviewAppsAndSubscriptions',
				path: 'apps',
				component: () =>
					import('../views/site/SiteOverviewAppsAndSubscriptions.vue'),
				props: true
			},
			{
				path: 'installing',
				component: () => import('../views/site/SiteInstalling.vue')
			},
			{
				path: 'analytics',
				component: () => import('../views/site/SiteCharts.vue')
			},
			{
				path: 'database',
				component: () => import('../views/site/SiteDatabase.vue')
			},
			{
				path: 'site-config',
				component: () => import('../views/site/SiteConfig.vue')
			},
			{
				path: 'setting',
				component: () => import('../views/site/SiteSettings.vue')
			},
			{
				path: 'console',
				component: () => import('../views/site/SiteConsole.vue')
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/site/SiteJobs.vue'),
				props: true
			},
			{
				path: 'logs/:logName?',
				component: () => import('../views/site/SiteLogs.vue'),
				props: true
			},
			{
				path: 'request-logs',
				component: () => import('../views/site/SiteRequestLogs.vue'),
				props: true
			},
			{
				path: 'auto-update',
				component: () => import('../views/site/SiteAutoUpdate.vue'),
				props: true
			}
		]
	},
	{
		path: '/servers',
		name: 'Servers',
		component: () => import('../views/server/Servers.vue')
	},
	{
		path: '/servers/new',
		name: 'NewServer',
		component: () => import('../views/server/NewServer.vue'),
		props: true
	},
	{
		path: '/servers/:serverName',
		name: 'Server',
		component: () => import('../views/server/Server.vue'),
		props: true,
		children: [
			{
				name: 'ServerOverview',
				path: 'overview',
				component: () => import('../views/server/ServerOverview.vue')
			},
			{
				name: 'ServerAnalytics',
				path: 'analytics',
				component: () => import('../views/server/ServerAnalytics.vue')
			},
			{
				name: 'ServerBenches',
				path: 'benches',
				component: () => import('../views/server/ServerBenches.vue')
			},
			{
				name: 'ServerJobs',
				path: 'jobs/:jobName?',
				component: () => import('../views/server/ServerJobs.vue'),
				props: true
			},
			{
				name: 'ServerPlays',
				path: 'plays/:playName?',
				component: () => import('../views/server/ServerPlays.vue'),
				props: true
			},
			{
				name: 'ServerInstall',
				path: 'install',
				component: () => import('../views/server/ServerInstall.vue'),
				props: true
			},
			{
				name: 'ServerSettings',
				path: 'setting',
				component: () => import('../views/server/ServerSettings.vue'),
				props: true
			}
		]
	},
	{
		name: 'New SelfHosted Server',
		path: '/selfhosted/new',
		component: () => import('../views/server/NewSelfHostedServer.vue'),
		props: true
	},
	{
		path: '/install-app/:marketplaceApp',
		name: 'InstallMarketplaceApp',
		component: () => import('@/views/marketplace/InstallMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/user-review/:marketplaceApp',
		name: 'ReviewMarketplaceApp',
		component: () => import('@/views/marketplace/ReviewMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/developer-reply/:marketplaceApp/:reviewId',
		name: 'ReplyMarketplaceApp',
		component: () => import('@/views/marketplace/ReplyMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/marketplace',
		name: 'Marketplace',
		component: () =>
			import(
				/* webpackChunkName: "marketplace" */ '../views/marketplace/Marketplace.vue'
			),
		children: [
			{
				path: 'publisher-profile',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplacePublisherProfile.vue'
					)
			},
			{
				path: 'apps',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplaceApps.vue'
					)
			},
			{
				path: 'payouts/:payoutOrderName?',
				component: () =>
					import(
						/* webpackChunkName: "marketplace" */ '../views/marketplace/MarketplacePayouts.vue'
					),
				props: true
			}
		]
	},
	{
		path: '/marketplace/apps/new',
		name: 'NewMarketplaceApp',
		component: () => import('../views/marketplace/NewMarketplaceApp.vue'),
		props: true
	},
	{
		path: '/marketplace/apps/:appName',
		name: 'MarketplaceApp',
		component: () => import('../views/marketplace/MarketplaceApp.vue'),
		props: true,
		children: [
			{
				name: 'MarketplaceAppOverview',
				path: 'overview',
				component: () =>
					import('../views/marketplace/MarketplaceAppOverview.vue')
			},
			{
				name: 'MarketplaceAppReview',
				path: 'review',
				component: () =>
					import('../views/marketplace/MarketplaceAppReview.vue'),
				props: true
			},
			{
				name: 'MarketplaceAppAnalytics',
				path: 'analytics',
				component: () =>
					import('../views/marketplace/MarketplaceAppAnalytics.vue')
			},
			{
				name: 'MarketplaceAppDeployment',
				path: 'releases',
				component: () =>
					import('../views/marketplace/MarketplaceAppDeployment.vue')
			},
			{
				name: 'MarketplaceAppSubscriptions',
				path: 'subscriptions',
				component: () =>
					import('../views/marketplace/MarketplaceAppSubscriptions.vue')
			},
			{
				name: 'MarketplaceAppPricing',
				path: 'pricing',
				component: () =>
					import('../views/marketplace/MarketplaceAppPricing.vue')
			}
		]
	},
	{
		path: '/spaces',
		name: 'Spaces',
		component: () => import('../views/spaces/Spaces.vue')
	},
	{
		path: '/codeservers/new',
		name: 'NewCodeServer',
		component: () => import('../views/spaces/NewCodeServer.vue')
	},
	{
		path: '/codeservers/:serverName',
		name: 'CodeServer',
		component: () => import('../views/spaces/CodeServer.vue'),
		props: true,
		children: [
			{
				name: 'CodeServerOverview',
				path: 'overview',
				component: () => import('../views/spaces/CodeServerOverview.vue')
			},
			{
				path: 'jobs/:jobName?',
				component: () => import('../views/spaces/CodeServerJobs.vue'),
				props: true
			}
		]
	},
	{
		path: '/setup-site/:product',
		name: 'App Site Setup',
		component: () => import('../views/site/AppSiteSetup.vue'),
		props: true,
		meta: {
			hideSidebar: true
		}
	},
	{
		path: '/subscription/:site?',
		name: 'Subscription',
		component: () => import('../views/checkout/Subscription.vue'),
		props: true,
		meta: {
			hideSidebar: true
		}
	},
	{
		path: '/billing/:invoiceName?',
		name: 'BillingScreen',
		component: () => import('../views/billing/AccountBilling.vue'),
		props: true
	},
	{
		path: '/settings',
		name: 'SettingsPage',
		component: () =>
			import(
				/* webpackChunkName: "account" */ '../views/settings/AccountSettings.vue'
			)
	},
	{
		name: 'NotFound',
		path: '/:pathMatch(.*)*',
		component: () => import('../views/general/404.vue')
	}
];

const router = createRouter({
	history: createWebHistory('/dashboard/'),
	routes
});

export default router;
