from typing import Final

from press.plans.server._types import ServerPlan
from press.plans.server.aws import _aws_server_plans
from press.plans.server.do import _do_server_plans
from press.plans.server.frappe import _frappe_compute_server_plans
from press.plans.server.hetzner import _hetzner_server_plans
from press.plans.server.oci import _oci_server_plans

_server_plans: Final[list[ServerPlan]] = [
	*_aws_server_plans,
	*_frappe_compute_server_plans,
	*_do_server_plans,
	*_oci_server_plans,
	*_hetzner_server_plans,
]
