import call from './call';

export default class Account {
	constructor() {
		this.user = null;
		this.team = null;
		this.ssh_key = null;
		this.teams = [];
		this.team_members = [];
		this.onboarding = null;
		this.balance = 0;
		this.feature_flags = {};
	}

	async fetchAccount() {
		if (document.cookie.includes('user_id=Guest;')) {
			return;
		}
		try {
			let result = await call('press.api.account.get');
			this.user = result.user;
			this.ssh_key = result.ssh_key;
			this.team = result.team;
			this.teams = result.teams;
			this.team_members = result.team_members;
			this.child_team_members = result.child_team_members;
			this.onboarding = result.onboarding;
			this.balance = result.balance;
			this.feature_flags = result.feature_flags;
			this.parent_team = result.parent_team;
		} catch (e) {
			localStorage.removeItem('current_team');
		}
	}

	hasRole(role) {
		let roles = this.user.roles.map(d => d.role);
		return roles.includes(role);
	}

	async switchTeam(team) {
		if (team === this.team.name) {
			return;
		}
		let result = await call('press.api.account.switch_team', { team });
		this.team = result.team;
		this.team_members = result.team_members;
		localStorage.setItem('current_team', team);
	}

	async switchToTeam(team) {
		await this.switchTeam(team);
		window.location.reload();
	}

	get needsCard() {
		return !this.hasBillingInfo;
	}

	get hasBillingInfo() {
		if (!this.team) {
			return true;
		}
		if (this.team.free_account || this.team.parent_team) {
			return true;
		}
		if (
			this.team.erpnext_partner ||
			this.team.payment_mode === 'Partner Credits'
		) {
			return true;
		}
		if (this.team.payment_mode == 'Card') {
			return this.team.default_payment_method;
		}
		if (this.team.payment_mode == 'Prepaid Credits') {
			return this.balance > 0;
		}
		return false;
	}
}
