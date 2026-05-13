from collections.abc import Callable
from typing import Literal, TypeAlias, cast

from press.plans.server import _server_plans
from press.plans.server._types import ServerPlan
from press.plans.site import _site_plans
from press.plans.site._types import SitePlan

PlanType: TypeAlias = Literal["Site", "Server"]

AnyPlan: TypeAlias = SitePlan | ServerPlan
FilterFn: TypeAlias = Callable[[AnyPlan], bool]

plan_type_select: dict[PlanType, list[AnyPlan]] = {
	"Site": cast("list[AnyPlan]", _site_plans),
	"Server": cast("list[AnyPlan]", _server_plans),
}


def get_plans(
	plan_type: PlanType,
	filter_fn: FilterFn | None = None,
) -> list[AnyPlan]:
	plans = plan_type_select[plan_type]
	if filter_fn is None:
		return plans

	return list(filter(filter_fn, plans))
