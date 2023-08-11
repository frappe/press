export default [
	{
		path: '/security',
		name: 'Security',
		component: () => import('../views/security/Servers.vue')
	},
	{
		path: '/security/:serverName',
		name: 'ServerSecurity',
		component: () => import('../views/security/Security.vue'),
		props: true,
		children: [
			{
				name: 'SecurityOverview',
				path: 'overview',
				component: () => import('../views/security/SecurityOverview.vue'),
				props: true
			},
			{
				name: 'SecurityUpdates',
				path: 'security_update/:updateId?',
				component: () => import('../views/security/SecurityUpdates.vue'),
				props: true
			},
			{
				name: 'Firewall',
				path: 'firewall/',
				// component: () => import('../views/security/SecurityUpdateInfo.vue'),
				props: true
			},
			{
				name: 'SSH Session Logs',
				path: 'ssh_session_logs/:logId?',
				component: () => import('../views/security/SSHSession.vue'),
				props: true
			},
			{
				name: 'Nginx Overview',
				path: 'nginx_overview/',
				// component: () => import('../views/security/SecurityUpdateInfo.vue'),
				props: true
			}
		]
	}
];
