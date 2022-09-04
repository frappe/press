import Home from '../views/Home.vue';
import siteRoutes from './site';
import saasRoutes from './saas';
import benchRoutes from './bench';
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
		component: () => import('../views/Welcome.vue')
	},
	...authRoutes,
	...benchRoutes,
	...siteRoutes,
	...saasRoutes,
	...marketplaceRoutes,
	{
		path: '/billing/:invoiceName?',
		name: 'BillingScreen',
		component: () => import('../views/AccountBilling.vue'),
		props: true
	},
	settingsRoute
];

const router = createRouter({
	history: createWebHistory('/dashboard/'),
	routes
});

export default router;
