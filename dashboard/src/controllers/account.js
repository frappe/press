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
		this._fetchAccountPromise = null;
	}

	async fetchIfRequired() {
		if (!this.user) {
			if (this._fetchAccountPromise) {
				await this._fetchAccountPromise;
			} else {
				await this.fetchAccount();
			}
		}
	}

	async fetchAccount() {
		if (document.cookie.includes('user_id=Guest;')) {
			return;
		}
		try {
			this._fetchAccountPromise = call('press.api.account.get');
			let result = await this._fetchAccountPromise;
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
			this.partner_email = result.partner_email;
			this.partner_billing_name = result.partner_billing_name;
			this.saas_site_request = result.saas_site_request;
			this.permissions = result.permissions;
			this.number_of_sites = result.number_of_sites;
			this.billing_info = result.billing_info;
		} catch (e) {
			localStorage.removeItem('current_team');
		} finally {
			this._fetchAccountPromise = null;
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
			this.team.payment_mode === 'Paid By Partner' ||
			this.team.payment_mode === 'Partner Credits'
		) {
			// partner credits shall be deprecated in few months
			return true;
		}
		if (['Card', 'Prepaid Credits'].includes(this.team.payment_mode)) {
			// card is chargeable and not spam
			return (
				this.billing_info.verified_micro_charge ||
				this.billing_info.has_paid_before ||
				this.balance > 0
			);
		}

		return false;
	}

	hasPermission(docname, action = '', list = false) {
		// logged in user is site owner or
		// has no granular permissions set, so has all permissions
		if (
			this.team.user === this.user.name ||
			Object.keys(this.permissions).length === 0
		) {
			return true;
		}
		// if any permission is set for resource, show list view
		if (Object.keys(this.permissions).includes(docname) && list) {
			return true;
		}
		// check for granular restricted access
		if (Object.keys(this.permissions).includes(docname)) {
			if (this.permissions[docname].includes(action)) {
				return true;
			}
		}
		return false;
	}
}
