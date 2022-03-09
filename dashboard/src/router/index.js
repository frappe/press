import Home from '../views/Home.vue';
import siteRoutes from './site';
import benchRoutes from './bench';
import accountRoute from './account';
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
	...marketplaceRoutes,
	accountRoute
];

const router = createRouter({
	history: createWebHistory('/dashboard/'),
	routes
});

export default router;
