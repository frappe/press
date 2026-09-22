import { createDocumentResource, frappeRequest } from 'frappe-ui'
import {
	clearImpersonatedTeam,
	getCurrentTeam,
	getImpersonatedTeam,
	setImpersonatedTeam,
	setSelectedTeam,
} from './currentTeam'

let team

export function getTeam() {
	if (!team) {
		team = createDocumentResource({
			doctype: 'Team',
			name: isLoggedIn() ? getCurrentTeam() : null,
			whitelistedMethods: {
				getTeamMembers: 'get_team_members',
				inviteTeamMember: 'invite_team_member',
				removeTeamMember: 'remove_team_member',
				cancelInvitation: 'cancel_invitation',
			},
		})
	}
	return team
}

function isLoggedIn() {
	return (
		document.cookie.includes('user_id') &&
		!document.cookie.includes('user_id=Guest')
	)
}

/** Switches the team in every tab. Use it for teams the user is a part of. */
export async function switchToTeam(team) {
	if (!(await canSwitchToTeam(team))) return
	setSelectedTeam(team)
	window.location.reload()
}

/** Switches the team in this tab alone, so the other tabs keep theirs. */
export async function impersonateTeam(team) {
	if (!(await canSwitchToTeam(team))) return
	setImpersonatedTeam(team)
	window.location.reload()
}

/** Returns this tab to the team the user picked for themselves. */
export function stopImpersonating() {
	clearImpersonatedTeam()
	window.location.reload()
}

async function canSwitchToTeam(team) {
	try {
		return await frappeRequest({
			url: '/api/method/press.api.account.can_switch_to_team',
			params: { team },
		})
	} catch (error) {
		console.log(error)
		return false
	}
}

export async function isLastSite(team) {
	let count = 0
	count = await frappeRequest({
		url: '/api/method/press.api.account.get_site_count',
		params: { team },
	})
	return Boolean(count === 1)
}

// Another tab switched the team the user is acting as. This tab is still
// showing the old team's data while its next request would carry the new one,
// so reload. Tabs pinned to a team of their own are left alone.
window.addEventListener('storage', (event) => {
	if (event.key !== 'current_team' || !event.newValue) return
	if (getImpersonatedTeam()) return
	window.location.reload()
})

window.switchToTeam = switchToTeam
window.impersonateTeam = impersonateTeam
