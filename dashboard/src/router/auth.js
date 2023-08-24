export default [
	{
		path: '/checkout',
		name: 'Checkout',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/checkout/Checkout.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/login/:forgot?',
		name: 'Login',
		component: () =>
			import(/* webpackChunkName: "login" */ '../views/auth/Login.vue'),
		meta: {
			isLoginPage: true
		},
		props: true
	},
	{
		path: '/signup',
		name: 'Signup',
		component: () =>
			import(/* webpackChunkName: "signup" */ '../views/auth/Signup.vue'),
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/setup-account/:requestKey/:joinRequest?',
		name: 'Setup Account',
		component: () =>
			import(
				/* webpackChunkName: "setup-account" */ '../views/auth/SetupAccount.vue'
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
				/* webpackChunkName: "reset-password" */ '../views/auth/ResetPassword.vue'
			),
		props: true,
		meta: {
			isLoginPage: true
		}
	},
	{
		path: '/impersonate/:team',
		name: 'Impersonate Team',
		component: () => import('../views/auth/ImpersonateTeam.vue'),
		props: true
	}
];
