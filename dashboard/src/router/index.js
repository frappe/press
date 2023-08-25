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
	{
		path: '/welcome',
		name: 'Welcome',
		component: () => import('../views/onboarding/Welcome.vue')
	},
	...authRoutes,
	...benchRoutes,
	...siteRoutes,
	...serverRoutes,
	...marketplaceRoutes,
	...spacesRoutes,
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
