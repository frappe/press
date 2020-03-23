import call from '../call';

export default {
	data() {
		return {
			user: null,
			team: null,
			teams: []
		};
	},
	created() {
		this.fetchAccount();
	},
	methods: {
		async fetchAccount() {
			let team = localStorage.getItem('current_team');
			let result = await call('press.api.account.get', { team });
			this.user = result.user;
			this.team = result.team;
			this.teams = result.teams;
			this.team_members = result.team_members;
			if (this.user.user_image) {
				let url = window.location.origin;
				url = url.replace('8080', '8000');
				this.user.user_image = url + this.user.user_image;
			}
		},
		async updateProfile() {
			let { first_name, last_name, email } = this.user;
			await this.$call('press.api.account.update_profile', {
				first_name,
				last_name,
				email
			});
			await this.fetchAccount();
		},
		hasRole(role) {
			let roles = this.user.roles.map(d => d.role);
			return roles.includes(role);
		},
		async switchToTeam(team) {
			if (team === this.team.name) {
				return;
			}
			let result = await this.$call('press.api.account.switch_team', { team });
			this.team = result.team;
			this.team_members = result.team_members;
			localStorage.setItem('current_team', team);
		}
	}
};
