import { createDocumentResource, frappeRequest } from 'frappe-ui';

let team;

export function getTeam() {
	if (!team) {
		team = createDocumentResource({
			doctype: 'Team',
			name: getCurrentTeam()
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
	return localStorage.getItem('current_team') || window.default_team;
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
