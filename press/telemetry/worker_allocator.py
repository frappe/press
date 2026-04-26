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


class BenchAllocation(TypedDict):
	bench: str
	weight: float
	max_web: int
	max_bg: int
	web_workers: float
	bg_workers: float


class AllocationResult(TypedDict):
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
		"""Returns the guaranteed web & background workers for a bench based on its site plan."""
		plan = PLAN_CONFIG.get(site_info["plan"])
		if not plan:
			print("Plan not found for site:", site_info["name"], "with plan:", site_info["plan"])
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

	def get_total_guaranteed_workers(self) -> tuple[float, float]:
		"""
		Returns the total guaranteed web + background workers for all benches.
		This calculation is done per site, assuming cases like
		Bench A [10 x 5USD + 1 x 50USD]; Bench B [1 x 50USD]
		Bench A should get more workers compared to Bench B
		"""
		total_guaranteed_web_workers = 0.0
		total_guaranteed_bg_workers = 0.0

		for bench in self.benches:
			for site in bench["site_info"]:
				guaranteed_web, guaranteed_bg = self.get_guaranteed_web_and_bg_workers(site)
				total_guaranteed_web_workers += guaranteed_web
				total_guaranteed_bg_workers += guaranteed_bg

		return total_guaranteed_web_workers, total_guaranteed_bg_workers

	def allocate_workers(self) -> list[dict[str, AllocationResult]]:
		"""
		Allocate workers to benches based on guaranteed limits and surplus distribution.
		"""
		total_guaranteed_web_workers, total_guaranteed_bg_workers = self.get_total_guaranteed_workers()

		if not self.can_server_accommodate_guaranteed_workers(
			total_guaranteed_web_workers, total_guaranteed_bg_workers
		):
			raise ResourceWarning(
				f"Server cannot accommodate the guaranteed workers for all benches. Required web workers: {total_guaranteed_web_workers}, "
				f"Required bg workers: {total_guaranteed_bg_workers}, Available web worker slots: {self.total_web_worker_slots}, "
				f"Available bg worker slots: {self.total_bg_worker_slots}"
			)

		bench_allocations = []
		total_server_weight = 0.0

		# Just in case we have no surplus left
		surplus_web_workers = max(self.total_web_worker_slots - total_guaranteed_web_workers, 0)
		surplus_bg_workers = max(self.total_bg_worker_slots - total_guaranteed_bg_workers, 0)

		for bench in self.benches:
			bench_weight = 0.0
			bench_web_workers = 0.0
			bench_bg_workers = 0.0
			max_web = 0
			max_bg = 0

			for site in bench["site_info"]:
				guaranteed_web, guaranteed_bg = self.get_guaranteed_web_and_bg_workers(site)
				bench_web_workers += guaranteed_web
				bench_bg_workers += guaranteed_bg
				bench_weight += PLAN_CONFIG.get(site["plan"], {}).get("weight", 1)
				max_web += PLAN_CONFIG.get(site["plan"], {}).get("web", {}).get("max", 1)
				max_bg += PLAN_CONFIG.get(site["plan"], {}).get("bg", {}).get("max", 1)

			bench_allocations.append(
				BenchAllocation(
					bench=bench["name"],
					weight=bench_weight,
					max_web=max_web,
					max_bg=max_bg,
					web_workers=bench_web_workers,
					bg_workers=bench_bg_workers,
				)
			)
			total_server_weight += bench_weight

		for b in bench_allocations:
			if total_server_weight > 0:
				# Raw calculations to get the bonus workers before applying the max limits
				web_bonus = (b["weight"] / total_server_weight) * surplus_web_workers
				bg_bonus = (b["weight"] / total_server_weight) * surplus_bg_workers

				raw_web = b["web_workers"] + web_bonus
				raw_bg = b["bg_workers"] + bg_bonus

				# Ensure we didn't exceed the max limits for the bench based on individual site plan maximums
				b["web_workers"] = min(b["max_web"], math.floor(raw_web))
				b["bg_workers"] = min(b["max_bg"], math.floor(raw_bg))

		return [
			{b["bench"]: {"web_workers": int(b["web_workers"]), "bg_workers": int(b["bg_workers"])}}
			for b in bench_allocations
		]


if __name__ == "__main__":
	scheduler = WorkerScheduler(
		benches=[
			BenchType(
				{
					"name": "Bench 1",
					"site_info": [
						# SiteInfo(name="Site A", plan="USD 5"),
						SiteInfo(name="Site B", plan="random"),
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
