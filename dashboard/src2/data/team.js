import { createDocumentResource } from 'frappe-ui';

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
	return document.cookie
		.split(';')
		.find(item => item.trim().startsWith('current_team='))
		?.split('=')[1];
}
