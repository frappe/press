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
		{
			name: 'NewBench',
			path: '/benches/new',
			component: () => import('./pages/NewBench.vue')
		},
		{
			path: '/settings',
			name: 'Settings',
			redirect: { name: 'ProfileSettings' },
			component: () => import('./pages/Settings.vue'),
			children: [
				{
					name: 'ProfileSettings',
					path: 'profile',
					component: () => import('./components/settings/ProfileSettings.vue')
				},
				{
					name: 'TeamSettings',
					path: 'team',
					component: () => import('./components/settings/TeamSettings.vue')
				},
				{
					path: 'permissions',
					name: 'PermissionsSettings',
					component: () => import('./components/settings/PermissionsSettings.vue'),
					redirect: { name: 'PermissionGroupList' },
					children: [
						{
							path: 'groups',
							name: 'PermissionGroupList',
							component: () => import('./components/settings/PermissionGroupList.vue'),
						},
						{
							props: true,
							path: 'groups/:groupId',
							name: 'PermissionGroupPermissions',
							component: () => import('./components/settings/PermissionGroupPermissions.vue'),
						}
					]
				},
			]
		},
		...generateRoutes()
	]
});

export default router;
