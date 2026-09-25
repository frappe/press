// The team the dashboard acts as, and the one every request is tagged with.
//
// A support agent needs to look at two customers side by side, so impersonation
// is kept in sessionStorage, which belongs to a single tab. The team the user
// picked for themselves stays in localStorage, which every tab shares.

const IMPERSONATED_TEAM = 'impersonated_team'
const SELECTED_TEAM = 'current_team'

export function getCurrentTeam() {
	return getImpersonatedTeam() || getSelectedTeam()
}

export function getImpersonatedTeam() {
	const team = sessionStorage.getItem(IMPERSONATED_TEAM)
	return isTeamAllowed(team) ? team : null
}

export function getSelectedTeam() {
	const team = localStorage.getItem(SELECTED_TEAM)
	if (isTeamAllowed(team)) return team

	// The stored team was disabled, or the user lost access to it.
	if (window.default_team)
		localStorage.setItem(SELECTED_TEAM, window.default_team)
	return window.default_team || null
}

/**
 * Namespaces a resource cache key to the tab's team.
 *
 * frappe-ui keeps one IndexedDB store for the whole origin and hydrates a
 * resource from it the moment the component mounts. Two tabs on different
 * teams would otherwise read each other's rows, so every key carries a team.
 */
export function teamCache(...parts) {
	return [getCurrentTeam(), ...parts]
}

/** True when the tab is showing a team the user is not a part of. */
export function isImpersonating() {
	const team = getCurrentTeam()
	return Boolean(team) && !belongsToUser(team)
}

export function setImpersonatedTeam(team) {
	sessionStorage.setItem(IMPERSONATED_TEAM, team)
}

export function setSelectedTeam(team) {
	sessionStorage.removeItem(IMPERSONATED_TEAM)
	localStorage.setItem(SELECTED_TEAM, team)
}

export function clearImpersonatedTeam() {
	sessionStorage.removeItem(IMPERSONATED_TEAM)
}

export function forgetTeams() {
	sessionStorage.removeItem(IMPERSONATED_TEAM)
	localStorage.removeItem(SELECTED_TEAM)
}

function belongsToUser(team) {
	if (!team) return false
	if (team === window.default_team) return true
	return (window.valid_teams || []).some((validTeam) => validTeam.name === team)
}

function isTeamAllowed(team) {
	if (!team) return false
	return Boolean(window.is_system_user) || belongsToUser(team)
}
