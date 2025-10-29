from enum import Enum


class ReleaseGroupActions(str, Enum):
	GenerateSSHCertificate = "Generate SSH Certificate"


class SiteActions(str, Enum):
	VisitSite = "Visit Site"
	ViewInDesk = "View in Desk"
	LoginAsAdmin = "Login As Administrator"


ACTIONS_RULES = {
	"Release Group": {
		ReleaseGroupActions.GenerateSSHCertificate: False,
	},
	"Site": {
		SiteActions.VisitSite: True,
		SiteActions.ViewInDesk: False,
		SiteActions.LoginAsAdmin: False,
	},
}
