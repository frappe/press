"""
This file is created to allocate workers for benches on public servers, depending on the
site plan and the number server resources available. The worker allocation is done by the following strategy

Guaranteed + Weighted Bonus

Guaranteed: Every bench gets a guaranteed number of workers, based on their site plans.
"""

import math
from dataclasses import dataclass
from typing import TypedDict


class SiteInfo(TypedDict):
	name: str
	plan: str


class BenchType(TypedDict):
	name: str
	site_info: list[SiteInfo]


class WorkerAllocation(TypedDict):
	web_workers: int
	bg_workers: int


# Plan configuration: (Min, Weight, Max)
# Arbitrary for now but seems fair enough considering the resources on public servers and the number of benches we have.
# Todo: Move this to fixtures with more plans [Large, Unlimited etc] and more accurate worker limits based on the plan.
PLAN_CONFIG: dict = {
	"USD 5": {"web": {"min": 1, "max": 2}, "bg": {"min": 1, "max": 1}, "weight": 1},
	"USD 10": {"web": {"min": 2, "max": 4}, "bg": {"min": 1, "max": 2}, "weight": 2},
	"USD 25": {"web": {"min": 4, "max": 8}, "bg": {"min": 2, "max": 4}, "weight": 5},
	"USD 50": {"web": {"min": 8, "max": 12}, "bg": {"min": 4, "max": 6}, "weight": 12},
}


@dataclass
class WorkerScheduler:
	benches: list[BenchType]
	total_web_worker_slots: float
	total_bg_worker_slots: float

	def get_guaranteed_web_and_bg_workers(self, site_info: SiteInfo) -> tuple[float, float]:
		"""Returns the guaranteed web + background workers for a bench based on its site plan."""
		plan = PLAN_CONFIG.get(site_info["plan"])

		if not plan:
			return 1, 1  # Default to min workers plan might be None/Trial etc

		return plan["web"]["min"], plan["bg"]["min"]

	def can_server_accommodate_guaranteed_workers(
		self, total_guaranteed_web_workers: float, total_guaranteed_bg_workers: float
	) -> bool:
		"""Checks if the server can accommodate the guaranteed workers for all benches."""
		return (
			self.total_web_worker_slots >= total_guaranteed_web_workers
			and self.total_bg_worker_slots >= total_guaranteed_bg_workers
		)

	def get_site_with_highest_weight(self, site_info_list: list[SiteInfo]) -> SiteInfo:
		"""Returns the site with the highest budget from a list of site info."""
		return max(
			site_info_list, key=lambda site_info: PLAN_CONFIG.get(site_info["plan"], {}).get("weight", 0)
		)

	def get_site_with_highest_max_workers(self, site_info_list: list[SiteInfo], worker_type: str) -> SiteInfo:
		"""Returns the site with the highest max workers for a given worker type from a list of site info."""
		return max(
			site_info_list,
			key=lambda site_info: PLAN_CONFIG.get(site_info["plan"], {}).get(worker_type, {}).get("max", 0),
		)

	def get_total_guaranteed_workers(self) -> tuple[float, float]:
		"""Returns the total guaranteed web + background workers for all benches."""
		total_guaranteed_web_workers = 0.0
		total_guaranteed_bg_workers = 0.0

		for bench in self.benches:
			site_with_highest_web_workers = self.get_site_with_highest_max_workers(bench["site_info"], "web")
			site_with_highest_bg_workers = self.get_site_with_highest_max_workers(bench["site_info"], "bg")

			total_guaranteed_web_workers += (
				PLAN_CONFIG.get(site_with_highest_web_workers["plan"], {}).get("web", {}).get("min", 0)
			)
			total_guaranteed_bg_workers += (
				PLAN_CONFIG.get(site_with_highest_bg_workers["plan"], {}).get("bg", {}).get("min", 0)
			)

		return total_guaranteed_web_workers, total_guaranteed_bg_workers

	def allocate_workers(self) -> list[dict[str, WorkerAllocation]] | None:
		"""
		Check if we can meet guaranteed worker limits for all benches.
			- If yes, check if there are surplus workers available
				- If yes, allocate surplus workers based on the priority weight of the plans.
				- If no, allocate only the guaranteed workers for each bench.

		- If no, Don't know what to do for now....
		"""
		total_guaranteed_web_workers, total_guaranteed_bg_workers = self.get_total_guaranteed_workers()

		if not self.can_server_accommodate_guaranteed_workers(
			total_guaranteed_web_workers, total_guaranteed_bg_workers
		):
			# Don't know what to do for now.
			return None

		bench_allocations = []
		total_server_weight = 0

		for bench in self.benches:
			# Assuming bench has multiple sites, we take the highest plan site
			top_site_weight = self.get_site_with_highest_weight(bench["site_info"])

			# guaranteed worker & weight calculation for largest site in the bench
			top_site_web = self.get_site_with_highest_max_workers(bench["site_info"], "web")
			top_site_bg = self.get_site_with_highest_max_workers(bench["site_info"], "bg")
			bench_weight = PLAN_CONFIG.get(top_site_weight["plan"], {}).get("weight", 0)
			max_web = PLAN_CONFIG.get(top_site_web["plan"], {}).get("web", {}).get("max", 0)
			max_bg = PLAN_CONFIG.get(top_site_bg["plan"], {}).get("bg", {}).get("max", 0)
			min_web = PLAN_CONFIG.get(top_site_web["plan"], {}).get("web", {}).get("min", 0)
			min_bg = PLAN_CONFIG.get(top_site_bg["plan"], {}).get("bg", {}).get("min", 0)

			bench_web_workers = min(min_web, max_web)
			bench_bg_workers = min(min_bg, max_bg)

			bench_allocations.append(
				{
					"bench": bench["name"],
					"weight": bench_weight,
					"max_web": max_web,
					"max_bg": max_bg,
					"web_workers": bench_web_workers,
					"bg_workers": bench_bg_workers,
				}
			)
			total_server_weight += bench_weight

		# Allocate surplus workers based on weight if there is any surplus
		surplus_web_workers = self.total_web_worker_slots - total_guaranteed_web_workers
		surplus_bg_workers = self.total_bg_worker_slots - total_guaranteed_bg_workers

		for b in bench_allocations:
			if total_server_weight > 0:
				# Some weighted bonus calculation
				web_bonus = (b["weight"] / total_server_weight) * surplus_web_workers
				bg_bonus = (b["weight"] / total_server_weight) * surplus_bg_workers

				raw_web = b["web_workers"] + web_bonus
				raw_bg = b["bg_workers"] + bg_bonus

				# Ensure we are not allocating more than the max limit for any bench
				b["web_workers"] = min(b["max_web"], math.floor(raw_web))
				b["bg_workers"] = min(b["max_bg"], math.floor(raw_bg))

		return [
			{b["bench"]: {"web_workers": b["web_workers"], "bg_workers": b["bg_workers"]}}
			for b in bench_allocations
		]


if __name__ == "__main__":
	scheduler = WorkerScheduler(
		benches=[
			BenchType(
				{
					"name": "Bench 1",
					"site_info": [
						SiteInfo(name="Site A", plan="USD 5"),
						SiteInfo(name="Site B", plan="USD 10"),
					],
				}
			),
			BenchType(
				{
					"name": "Bench 1",
					"site_info": [
						SiteInfo(name="Site C", plan="USD 25"),
						SiteInfo(name="Site D", plan="USD 50"),
					],
				}
			),
		],
		total_web_worker_slots=20,
		total_bg_worker_slots=10,
	)
	print(scheduler.allocate_workers())
