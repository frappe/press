import router from './index';

export default function registerRouter(app, auth, account) {
	app.use(router);

	router.beforeEach(async (to, from, next) => {
		// TODO: Remove once the new signup flow is live,
		// currently this is being called for every guest request which breaks the current signup flow
		// await account.fetchIfRequired();

		if (account.saas_site_request && to.name != 'App Site Setup') {
			next({
				name: 'App Site Setup',
				params: { product: account.saas_site_request }
			});
			return;
		}

		if (to.name == 'Home') {
			next({ name: 'Sites' });
			return;
		}

		if (to.matched.some(record => !record.meta.isLoginPage)) {
			// this route requires auth, check if logged in
			// if not, redirect to login page.
			if (!auth.isLoggedIn) {
				next({ name: 'Login', query: { route: to.path } });
			} else {
				next();
			}
		} else {
			// if already logged in, route to /sites
			if (auth.isLoggedIn) {
				if (!account.user) {
					await account.fetchAccount();
				}
				if (to?.query?.route) {
					next({ path: to.query.route });
				} else {
					next({ name: 'Sites' });
				}
			} else {
				next();
			}
		}
	});
}
