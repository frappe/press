import call from '../call';

export default {
	data() {
		return {
			user: null
		};
	},
	created() {
		this.fetchAccount();
	},
	methods: {
		async fetchAccount() {
			this.user = await call('press.api.account.get');
			if (this.user.image) {
				let url = window.location.origin;
				url = url.replace('8080', '8000');
				this.user.image = url + this.user.image;
			}
		},
		async updateProfile() {
			let { first_name, last_name, email } = this.$store.account.user;
			await this.$call('press.api.account.update_profile', {
				first_name,
				last_name,
				email
			});
			await this.fetchAccount();
		}
	}
};
