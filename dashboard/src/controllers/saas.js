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

		this.isSaasLogin = this.cookie.user_id && this.cookie.user_id !== 'Guest';
	}

	wasSaasLogout() {
		return Boolean(localStorage.getItem('was_saas_logout'));
	}
	switchToSaas(site) {
		localStorage.removeItem('current_saas_site');
		localStorage.setItem('current_saas_site', site);
		window.location.reload();
	}
	loginToSaas(site) {
		localStorage.removeItem('current_saas_site');
		this.isSaasLogin = true;
		localStorage.setItem('current_saas_site', site);
	}
}
