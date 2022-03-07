import call from './call';
import Vue from 'vue';

export default class Auth {
	constructor() {
		this.isLoggedIn = false;
		this.user = null;
		this.user_image = null;
		this.cookie = null;

		this.cookie = Object.fromEntries(
			document.cookie
				.split('; ')
				.map(part => part.split('='))
				.map(d => [d[0], decodeURIComponent(d[1])])
		);

		this.isLoggedIn = this.cookie.user_id && this.cookie.user_id !== 'Guest';
	}

	async login(email, password) {
		localStorage.removeItem('current_team');
		let res = await call('login', {
			usr: email,
			pwd: password
		});
		if (res) {
			await this.$account.fetchAccount();
			localStorage.setItem('current_team', this.$account.team.name);
			this.isLoggedIn = true;
			return res;
		}
		return false;
	}
	async logout() {
		localStorage.removeItem('current_team');
		await call('logout');
		window.location.reload();
	}
	async resetPassword(email) {
		return await call('press.api.account.send_reset_password_email', {
			email
		});
	}
}
