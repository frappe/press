from enum import Enum


class ReleaseGroupActions(str, Enum):
	SSHAccess = "SSH Access"
	ManageApps = "Manage Apps"


class ServerActions(str, Enum):
	SSHAccess = "SSH Access"


class SiteActions(str, Enum):
	VisitSite = "Visit Site"
	ViewInDesk = "View in Desk"
	LoginAsAdmin = "Login As Administrator"
	ManageApps = "Manage Apps"


ACTIONS_RULES = {
	"Release Group": {
		ReleaseGroupActions.SSHAccess.value: False,
		ReleaseGroupActions.ManageApps.value: False,
	},
	"Server": {
		ServerActions.SSHAccess.value: False,
	},
	"Site": {
		SiteActions.VisitSite.value: True,
		SiteActions.ViewInDesk.value: False,
		SiteActions.LoginAsAdmin.value: False,
		SiteActions.ManageApps.value: False,
	},
}
