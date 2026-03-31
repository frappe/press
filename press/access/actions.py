from enum import Enum


class ReleaseGroupActions(str, Enum):
	SSHAccess = "SSH Access"


class SiteActions(str, Enum):
	VisitSite = "Visit Site"
	ViewInDesk = "View in Desk"
	LoginAsAdmin = "Login As Administrator"


ACTIONS_RULES = {
	"Release Group": {
		ReleaseGroupActions.SSHAccess.value: False,
	},
	"Site": {
		SiteActions.VisitSite.value: True,
		SiteActions.ViewInDesk.value: False,
		SiteActions.LoginAsAdmin.value: False,
	},
}
