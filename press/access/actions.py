from enum import Enum


class SiteActions(Enum):
	VISIT_SITE = "Visit Site"
	VIEW_IN_DESK = "View in Desk"
	LOGIN_AS_ADMINISTRATOR = "Login As Administrator"


ACTIONS_RULES = {
	"Site": {
		SiteActions.VISIT_SITE: True,
		SiteActions.VIEW_IN_DESK: False,
		SiteActions.LOGIN_AS_ADMINISTRATOR: False,
	}
}
