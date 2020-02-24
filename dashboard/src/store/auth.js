import router from '@/router';
export default {
	data() {
		return {
			isLoggedIn: false,
			user: null
		};
	},
	created() {
		this.isLoggedIn =
			document.cookie && !document.cookie.includes('user_id=Guest');
	},
	methods: {
		async login(email, password) {
			let res = await this.$call('login', {
				usr: email,
				pwd: password
            });
			if (res === 'Logged In') {
				this.isLoggedIn = true;
				return true;
			}
			return false;
		},
		async logout() {
			await this.$call('logout');
			this.isLoggedIn = false;
			router.push('/login');
		}
	}
};
