import router from './index';

export default function registerRouter(app, auth, account) {
	app.use(router);

	router.beforeEach(async (to, from, next) => {
		if (to.name == 'Home') {
			next({ name: 'Welcome' });
			return;
		}

		if (to.matched.some(record => !record.meta.isLoginPage)) {
			// this route requires auth, check if logged in
			// if not, redirect to login page.
			if (!auth.isLoggedIn) {
				next({ name: 'Login', query: { route: to.path } });
			} else {
				if (!account.user) {
					await account.fetchAccount();
				}
				next();
			}
		} else {
			// if already logged in, route to /welcome
			if (auth.isLoggedIn) {
				if (!account.user) {
					await account.fetchAccount();
				}
				next({ name: 'Welcome' });
			} else {
				next();
			}
		}
	});
}
