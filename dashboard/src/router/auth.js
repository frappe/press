export default [
	{
		path: '/login/:forgot?',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/Login.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/signup',
		name: 'Signup',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/Signup.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/setup-account/:requestKey/:joinRequest?',
		name: 'Setup Account',
		component: () =>
			import(
				/* webpackChunkName: "setup-account" */ '../views/SetupAccount.vue'
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
				/* webpackChunkName: "reset-password" */ '../views/ResetPassword.vue'
			),
		props: true,
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/impersonate/:team',
		name: 'Impersonate Team',
		component: () => import('../views/ImpersonateTeam.vue'),
		props: true
	}
];
