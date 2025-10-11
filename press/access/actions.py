from enum import Enum


class ReleaseGroupActions(Enum):
	GENERATE_SSH_CERTIFICATE = "Generate SSH Certificate"


class SiteActions(Enum):
	VISIT_SITE = "Visit Site"
	VIEW_IN_DESK = "View in Desk"
	LOGIN_AS_ADMINISTRATOR = "Login As Administrator"


ACTIONS_RULES = {
	"Release Group": {
		ReleaseGroupActions.GENERATE_SSH_CERTIFICATE: False,
	},
	"Site": {
		SiteActions.VISIT_SITE: True,
		SiteActions.VIEW_IN_DESK: False,
		SiteActions.LOGIN_AS_ADMINISTRATOR: False,
	},
}
