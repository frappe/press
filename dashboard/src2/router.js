import { createRouter, createWebHistory } from 'vue-router';
import generateRoutes from './objects/generateRoutes';

let router = createRouter({
	history: createWebHistory('/dashboard2/'),
	routes: [
		{
			path: '/',
			component: () => import('./pages/Home.vue'),
			redirect: '/sites'
		},
		{
			name: 'JobPage',
			path: '/jobs/:id',
			component: () => import('./pages/JobPage.vue'),
			props: true
		},
		{
			name: 'NewSite',
			path: '/sites/new',
			component: () => import('./pages/NewSite.vue')
		},
		...generateRoutes()
	]
});

export default router;
