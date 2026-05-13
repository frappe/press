from typing import Final

from press.plans.site._types import SitePlan
from press.plans.site.plans import _site_plans

site_plans: Final[list[SitePlan]] = [*_site_plans]
