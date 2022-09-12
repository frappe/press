import Home from '../views/general/Home.vue';
import siteRoutes from './site';
import saasRoutes from './saas';
import benchRoutes from './bench';
import serverRoutes from './server';
import settingsRoute from './settings';
import authRoutes from './auth';
import marketplaceRoutes from './marketplace';

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
	...saasRoutes,
	...marketplaceRoutes,
	{
		path: '/billing/:invoiceName?',
		name: 'BillingScreen',
		component: () => import('../views/billing/AccountBilling.vue'),
		props: true
	},
	{
		path: '/404NotFound',
		name: '404NotFound',
		component: () => import('../views/general/404.vue')
	},
	settingsRoute,
	{
		path: '/:pathMatch(.*)*',
		name: 'NotFound',
		component: () => import('../views/general/404.vue')
	}
];

const router = createRouter({
	history: createWebHistory('/dashboard/'),
	routes
});

export default router;
