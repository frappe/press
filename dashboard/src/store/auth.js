import router from '@/router';
export default {
	data() {
		return {
			isLoggedIn: false,
			user: null,
			user_image: null,
			cookie: null,
			csrf_token: null
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
			if (res === 'Logged In') {
				this.$store.account.fetchAccount();
				this.isLoggedIn = true;
				return true;
			}
			return false;
		},
		async logout() {
			await this.$call('logout');
			this.isLoggedIn = false;
			router.push('/login');
			window.location.reload();
		}
	}
};
