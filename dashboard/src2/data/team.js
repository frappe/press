import { createDocumentResource, frappeRequest } from 'frappe-ui';

let team;

export function getTeam() {
	if (!team) {
		team = createDocumentResource({
			doctype: 'Team',
			name: getCurrentTeam(),
			whitelistedMethods: {
				getTeamMembers: 'get_team_members',
				removeTeamMember: 'remove_team_member',
				changeDefaultDashboard: 'change_default_dashboard'
			}
		});
	}
	return team;
}

function getCurrentTeam() {
	if (
		document.cookie.includes('user_id=Guest;') ||
		!document.cookie.includes('user_id')
	) {
		throw new Error('Not logged in');
	}
	let currentTeam = localStorage.getItem('current_team');
	if (
		!currentTeam ||
		(currentTeam !== window.default_team &&
			!window.valid_teams.map(t => t.name).includes(currentTeam) &&
			!window.is_system_user)
	) {
		currentTeam = window.default_team;
		localStorage.setItem('current_team', currentTeam);
	}
	return currentTeam;
}

export async function switchToTeam(team) {
	let canSwitch = false;
	try {
		canSwitch = await frappeRequest({
			url: '/api/method/press.api.account.can_switch_to_team',
			params: { team }
		});
	} catch (error) {
		console.log(error);
		canSwitch = false;
	}
	if (canSwitch) {
		localStorage.setItem('current_team', team);
		window.location.reload();
	}
}

window.switchToTeam = switchToTeam;
