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

		this.isSaasLogin = this.cookie.user_id && this.cookie.user_id !== 'Guest';
	}
	saasLogin() {
		localStorage.setItem('saas_login', true);
		window.location.reload();
	}
}
