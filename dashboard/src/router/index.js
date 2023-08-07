import Home from '../views/general/Home.vue';
import authRoutes from './auth';
import siteRoutes from './site';
import benchRoutes from './bench';
import serverRoutes from './server';
import settingsRoute from './settings';
import billingRoute from './billing';
import marketplaceRoutes from './marketplace';
import spacesRoutes from './spaces';

import { createRouter, createWebHistory } from 'vue-router';

const routes = [
	{
		path: '/',
		name: 'Home',
		component: Home
	},
	...authRoutes,
	...benchRoutes,
	...siteRoutes,
	...serverRoutes,
	...marketplaceRoutes,
	...spacesRoutes,
	{
		path: '/setup-site/:product',
		name: 'App Site Setup',
		component: () => import('../views/site/AppSiteSetup.vue'),
		props: true,
		meta: {
			hideSidebar: true
		}
	},
	billingRoute,
	settingsRoute,
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
