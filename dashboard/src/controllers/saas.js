import call from './call';

export default class Saas {
	constructor() {
		this.isSaasLogin = false;
		this.cookie = null;

		this.cookie = Object.fromEntries(
			document.cookie
				.split('; ')
				.map(part => part.split('='))
				.map(d => [d[0], decodeURIComponent(d[1])])
		);
		this.sub = async () => {
		// returns a random active saas subscription for team for loading default view of saas dashboard
			let team = localStorage.getItem('current_team');
			return await call('press.api.saas.get_saas_site_and_app', { team })
		};

		this.isSaasLogin = this.cookie.user_id && this.cookie.user_id !== 'Guest';
	}


	wasSaasLogout() {
		return Boolean(localStorage.getItem('was_saas_logout'));
	}
	switchToSaas(site, app) {
		localStorage.removeItem('current_saas_site');
		localStorage.removeItem('current_saas_app');
		localStorage.setItem('current_saas_site', site);
		localStorage.setItem('current_saas_app', app);
		window.location.reload();
	}
	async loginToSaas(isLogin, site, app) {
		localStorage.removeItem('current_saas_site');
		localStorage.removeItem('current_saas_app');

		if (isLogin) {
			this.isSaasLogin = true;
			let res = await this.sub();
			site = res.site;
			app = res.app;
		}

		localStorage.setItem('current_saas_site', site);
		localStorage.setItem('current_saas_app', app);
		window.location.reload();
	}
}
