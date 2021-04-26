import Vue from 'vue';
import call from './call';

export default new Vue({
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
			if (document.cookie.includes('user_id=Guest;')) {
				return;
			}
			let result = await call('press.api.account.get');
			this.user = result.user;
			this.team = result.team;
			this.teams = result.teams;
			this.team_members = result.team_members;
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
			window.location.reload();
		}
	},
	computed: {
		needsCard() {
			return !this.hasBillingInfo;
		},
		hasBillingInfo() {
			if (!this.team) return true;
			return (
				this.team.default_payment_method ||
				this.team.erpnext_partner ||
				this.team.free_account
			);
		}
	}
});
