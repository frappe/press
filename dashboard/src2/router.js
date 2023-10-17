import { createRouter, createWebHistory } from 'vue-router';
import { generateRoutes } from './objects';

let router = createRouter({
	history: createWebHistory('/dashboard2/'),
	routes: [
		{
			path: '/',
			component: () => import('./pages/Home.vue')
		},
		...generateRoutes()
	]
});

export default router;
