import Vue from 'vue';

export default new Vue({
	data() {
		return {
			isLoggedIn: false,
			user: null,
			user_image: null,
			cookie: null
		};
	},
	created() {
		this.cookie = Object.fromEntries(
			document.cookie
				.split('; ')
				.map(part => part.split('='))
				.map(d => [d[0], decodeURIComponent(d[1])])
		);

		this.isLoggedIn = this.cookie.user_id && this.cookie.user_id !== 'Guest';
	},
	methods: {
		async login(email, password) {
			let res = await this.$call('login', {
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
		},
		async logout() {
			localStorage.removeItem('current_team');
			await this.$call('logout');
			window.location.reload();
		},
		async resetPassword(email) {
			return await this.$call('press.api.account.send_reset_password_email', {
				email
			});
		}
	}
});
