"""
This file is created to allocate workers for benches on public servers, depending on the
site plan and the number server resources available. The worker allocation is done by the following strategy

Guaranteed + Weighted Bonus

Guaranteed: Every bench gets a guaranteed number of workers, based on their site plans.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypedDict


class SiteInfo(TypedDict):
	name: str
	plan: str


class AllocationResult(TypedDict):
	web_workers: int
	bg_workers: int


@dataclass
class BenchType:
	name: str
	site_info: list[SiteInfo]
	# Config coming from release group, this can reduce the number of workers by a factor
	threads_per_worker: int = 0
	# Config coming from release group
	# This needs to be respected as well if not set to 0
	min_web_workers: int = 0
	min_bg_workers: int = 0
	max_web_workers: int = 0
	max_bg_workers: int = 0


@dataclass
class BenchAllocation:
	bench: str
	weight: float
	max_web: int
	max_bg: int
	web_workers: float
	bg_workers: float
	release_group_web_worker_min_limit: float = 0
	release_group_web_worker_max_limit: float = 0
	release_group_bg_worker_max_limit: float = 0
	release_group_bg_worker_min_limit: float = 0


@dataclass
class WorkerConfig:
	share: float
	max: int

	def effective_share(self, threads: int) -> float:
		"""Get the effective share of workers from the pool for this bench given the number of threads per worker."""
		return self.share / threads if threads else self.share

	def effective_max(self, threads: int) -> int:
		"""Get the effective max number of workers for this bench given the number of threads per worker."""
		# Using ciel here since floor is mostly going to give a 0
		return max(1, math.ceil(self.max / threads)) if threads else self.max


@dataclass
class PlanConfig:
	web: WorkerConfig
	bg: WorkerConfig
	weight: int

	def get_web_share(self, threads: int) -> float:
		return self.web.effective_share(threads)

	def get_web_max(self, threads: int) -> int:
		return self.web.effective_max(threads)

	def get_bg_share(self) -> float:
		return self.bg.share

	def get_bg_max(self) -> int:
		return self.bg.max


# Arbitrary for now but seems fair enough considering the resources on public servers and the number of benches we have.
# Todo: Move this to fixtures with more plans [Large, Unlimited etc] and more accurate worker limits based on the plan.
# We are now not concidering floor of guaranteed workers, we are concidering the pool share that we guarantee to each plan
# We are capping the max workers to 12 and utilizing g - threads worker class (https://gunicorn.org/design/#how-many-workers)

PLAN_CONFIG: dict[str, PlanConfig] = {
	"SaaS Trial": PlanConfig(
		web=WorkerConfig(share=0.1, max=1), bg=WorkerConfig(share=0.05, max=1), weight=1
	),
	"Trial": PlanConfig(web=WorkerConfig(share=0.1, max=1), bg=WorkerConfig(share=0.05, max=1), weight=1),
	"USD 5": PlanConfig(web=WorkerConfig(share=0.25, max=2), bg=WorkerConfig(share=0.1, max=1), weight=2),
	"USD 10": PlanConfig(web=WorkerConfig(share=0.5, max=4), bg=WorkerConfig(share=0.25, max=2), weight=4),
	"USD 25": PlanConfig(web=WorkerConfig(share=0.75, max=8), bg=WorkerConfig(share=0.5, max=4), weight=8),
	"USD 37.5": PlanConfig(
		web=WorkerConfig(share=0.75, max=10), bg=WorkerConfig(share=0.5, max=5), weight=10
	),
	"USD 50": PlanConfig(web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=0.75, max=6), weight=14),
	"USD 75": PlanConfig(web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=0.75, max=6), weight=20),
	"USD 100": PlanConfig(web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=1.0, max=6), weight=26),
	"USD 200": PlanConfig(web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=1.0, max=6), weight=32),
	"Frappe Team": PlanConfig(
		web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=1.0, max=6), weight=26
	),
	"Frappe Team High": PlanConfig(
		web=WorkerConfig(share=1.0, max=12), bg=WorkerConfig(share=1.0, max=6), weight=32
	),
}


def get_plan_config(plan_name: str) -> PlanConfig:
	"""Helper function to get the plan config, returns a default config if the plan is not found."""
	return PLAN_CONFIG.get(
		plan_name,
		PlanConfig(web=WorkerConfig(share=0.1, max=1), bg=WorkerConfig(share=0.05, max=1), weight=1),
	)


@dataclass
class WorkerAllocator:
	benches: list[BenchType]
	total_web_worker_slots: float
	total_bg_worker_slots: float
	allow_surplus: bool = True

	def get_guaranteed_web_and_bg_worker_share(
		self, site_info: SiteInfo, threads: int = 0
	) -> tuple[float, float]:
		"""Returns the guaranteed web & background workers for a bench based on its site plan."""
		plan_config = get_plan_config(site_info["plan"])
		return plan_config.get_web_share(threads=threads), plan_config.get_bg_share()

	def can_server_accommodate_guaranteed_workers(
		self, total_guaranteed_web_workers: float, total_guaranteed_bg_workers: float
	) -> bool:
		"""Checks if the server can accommodate the guaranteed workers for all benches."""
		# We are checking against the share of workers we need to guarantee instead of the raw number of them
		# Therefore we can utilize resources more freely.
		return (
			self.total_web_worker_slots >= total_guaranteed_web_workers
			and self.total_bg_worker_slots >= total_guaranteed_bg_workers
		)

	def get_sorted_sites(self, bench: BenchType) -> list[SiteInfo]:
		"""Sort sites based on plan"""
		return sorted(bench.site_info, key=lambda x: get_plan_config(x["plan"]).weight, reverse=True)

	@staticmethod
	def get_decay_factor(idx: int) -> float:
		"""Get the decay factor based on the index of the site in the bench to ensure
		benches with large number of sites (standby) are not eating most of the workers."""
		if idx < 10:
			decay_factor = 1.0

		elif idx < 50:
			decay_factor = 0.75

		else:
			decay_factor = 0.5

		return decay_factor

	def get_total_guaranteed_worker_share(self) -> tuple[float, float]:
		"""
		Returns the total guaranteed web + background workers for all benches.
		This calculation is done per site, assuming cases like
		Bench A [10 x 5USD + 1 x 50USD]; Bench B [1 x 50USD]
		Bench A should get more workers compared to Bench B
		We also account for public benches with standby sites to ensure they aren't eating most of
		the workers
		"""
		total_web = 0.0
		total_bg = 0.0

		for bench in self.benches:
			bench_web = 0.0
			bench_bg = 0.0
			sorted_sites = self.get_sorted_sites(bench)

			for idx, site in enumerate(sorted_sites):
				guaranteed_web, guaranteed_bg = self.get_guaranteed_web_and_bg_worker_share(
					site, bench.threads_per_worker
				)
				decay_factor = self.get_decay_factor(idx)
				bench_web += guaranteed_web * decay_factor
				bench_bg += guaranteed_bg * decay_factor

			# Respect release group minimums in the guarantee check
			total_web += max(bench_web, bench.min_web_workers)
			total_bg += max(bench_bg, bench.min_bg_workers)

		return total_web, total_bg

	def apply_release_group_limits(self, bench_allocation: BenchAllocation) -> None:
		"""Apply release group level limits on bench after the allocation is done"""
		if bench_allocation.release_group_web_worker_max_limit:
			bench_allocation.web_workers = min(
				bench_allocation.web_workers, bench_allocation.release_group_web_worker_max_limit
			)
		if bench_allocation.release_group_bg_worker_max_limit:
			bench_allocation.bg_workers = min(
				bench_allocation.bg_workers, bench_allocation.release_group_bg_worker_max_limit
			)

		if bench_allocation.web_workers < bench_allocation.release_group_web_worker_min_limit:
			bench_allocation.web_workers = bench_allocation.release_group_web_worker_min_limit

		if bench_allocation.bg_workers < bench_allocation.release_group_bg_worker_min_limit:
			bench_allocation.bg_workers = bench_allocation.release_group_bg_worker_min_limit

	def account_for_web_worker_shootoff(
		self,
		bench_allocations: list[BenchAllocation],
		total_allocated_workers: float,
		total_server_weight: float,
	) -> None:
		"""Trim web workers respecting the release group minimum limits also ensuring at least one worker"""
		over = total_allocated_workers - math.floor(self.total_web_worker_slots)
		if over <= 0:
			return

		for b in sorted(bench_allocations, key=lambda x: x.weight):
			if over <= 0:
				break

			# Floor is the higher of 1 or the release group minimum
			floor = max(1, b.release_group_web_worker_min_limit)
			headroom = b.web_workers - floor
			if headroom <= 0:
				continue

			proportional_trim = math.ceil((b.weight / total_server_weight) * over)
			reduction = min(proportional_trim, headroom)  # never below floor
			b.web_workers -= reduction
			over -= reduction

		if over > 0:
			raise ResourceWarning(f"Unable to account for web worker shootoff. Over allocated by: {over}")

	def account_for_bg_worker_shootoff(  # noqa: C901
		self,
		bench_allocations: list[BenchAllocation],
		total_allocated_workers: float,
		total_server_weight: float,
	) -> None:
		"""Trim bg workers respecting the release group minimum limits also ensuring at least one worker"""
		over = total_allocated_workers - math.floor(self.total_bg_worker_slots)
		if over <= 0:
			return

		# trim benches with no release group minimum set
		for b in sorted(bench_allocations, key=lambda x: x.weight):
			if over <= 0:
				break
			if b.release_group_bg_worker_min_limit:
				continue

			headroom = b.bg_workers - 1
			if headroom <= 0:
				continue

			proportional_trim = math.ceil((b.weight / total_server_weight) * over)
			reduction = min(proportional_trim, headroom)
			b.bg_workers -= reduction
			over -= reduction

		if over > 0:
			for b in sorted(bench_allocations, key=lambda x: x.weight):
				if over <= 0:
					break
				if not b.release_group_bg_worker_min_limit:
					continue  # Previous case

				floor = max(1, b.release_group_bg_worker_min_limit)
				headroom = b.bg_workers - floor
				if headroom <= 0:
					continue

				proportional_trim = math.ceil((b.weight / total_server_weight) * over)
				reduction = min(proportional_trim, headroom)
				b.bg_workers -= reduction
				over -= reduction

		if over > 0:
			raise ResourceWarning(f"Unable to account for bg worker shootoff. Over allocated by: {over}")

	def calculate_weight_distribution(
		self,
		total_server_weight: float,
		surplus_web_workers: float,
		surplus_bg_workers: float,
		bench_allocations: list[BenchAllocation],
	) -> None:
		"""In place update the bench allocations with the bonus workers based on the surplus.
		This also accounts for release group level limits set on the workers
		"""
		for bench_allocation in bench_allocations:
			if total_server_weight > 0:
				# Raw calculations to get the bonus workers before applying the max limits
				if self.allow_surplus:
					web_bonus = (bench_allocation.weight / total_server_weight) * surplus_web_workers
					bg_bonus = (bench_allocation.weight / total_server_weight) * surplus_bg_workers
					raw_web = bench_allocation.web_workers + web_bonus
					raw_bg = bench_allocation.bg_workers + bg_bonus

					# Ensure we didn't exceed the max limits for the bench based on individual site plan maximums
					# Also ensure we are giving at least one worker to the bench regardless of the calculations.
					bench_allocation.web_workers = max(min(bench_allocation.max_web, math.floor(raw_web)), 1)
					bench_allocation.bg_workers = max(min(bench_allocation.max_bg, math.floor(raw_bg)), 1)
				else:
					bench_allocation.web_workers = max(
						min(bench_allocation.max_web, math.floor(bench_allocation.web_workers)), 1
					)
					bench_allocation.bg_workers = max(
						min(bench_allocation.max_bg, math.floor(bench_allocation.bg_workers)), 1
					)

			self.apply_release_group_limits(bench_allocation)

		total_allocated_web_workers = sum(b.web_workers for b in bench_allocations)
		total_allocated_bg_workers = sum(b.bg_workers for b in bench_allocations)

		self.account_for_web_worker_shootoff(
			bench_allocations, total_allocated_web_workers, total_server_weight
		)
		self.account_for_bg_worker_shootoff(
			bench_allocations, total_allocated_bg_workers, total_server_weight
		)

	def allocate_workers(self) -> list[dict[str, AllocationResult]]:
		"""
		Allocate workers to benches based on guaranteed limits and surplus distribution.
		"""
		total_guaranteed_web_workers, total_guaranteed_bg_workers = self.get_total_guaranteed_worker_share()

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
			threads = bench.threads_per_worker

			sorted_sites = self.get_sorted_sites(bench)

			for idx, site in enumerate(sorted_sites):
				plan_config = get_plan_config(site["plan"])
				guaranteed_web, guaranteed_bg = self.get_guaranteed_web_and_bg_worker_share(
					site,
					threads,
				)

				decay_factor = self.get_decay_factor(idx)

				bench_web_workers += guaranteed_web * decay_factor
				bench_bg_workers += guaranteed_bg * decay_factor
				bench_weight += plan_config.weight
				max_web += plan_config.get_web_max(threads)
				max_bg += plan_config.get_bg_max()

			bench_allocations.append(
				BenchAllocation(
					bench=bench.name,
					weight=bench_weight,
					# Plan level cap calculations
					max_web=max_web,
					max_bg=max_bg,
					web_workers=bench_web_workers,
					bg_workers=bench_bg_workers,
					# Included the release group caps
					release_group_web_worker_max_limit=bench.max_web_workers,
					release_group_bg_worker_max_limit=bench.max_bg_workers,
					release_group_web_worker_min_limit=bench.min_web_workers,
					release_group_bg_worker_min_limit=bench.min_bg_workers,
				)
			)
			total_server_weight += bench_weight

		self.calculate_weight_distribution(
			total_server_weight, surplus_web_workers, surplus_bg_workers, bench_allocations
		)

		return [
			{b.bench: {"web_workers": int(b.web_workers), "bg_workers": int(b.bg_workers)}}
			for b in bench_allocations
		]


if __name__ == "__main__":
	scheduler = WorkerAllocator(
		benches=[
			BenchType(
				name="Bench 1",
				site_info=[
					# SiteInfo(name="Site A", plan="USD 5"),
					SiteInfo(name="Site B", plan="USD 10"),
				],
			),
			BenchType(
				name="Bench 2",
				site_info=[
					SiteInfo(name="Site C", plan="USD 10"),
					SiteInfo(name="Site C", plan="USD 10"),
					SiteInfo(name="Site D", plan="USD 50"),
				],
			),
			BenchType(
				name="Bench 3",
				site_info=[
					SiteInfo(name="Site A", plan="USD 5"),
					SiteInfo(name="Site B", plan="USD 5"),
					SiteInfo(name="Site B", plan="USD 5"),
					SiteInfo(name="Site B", plan="USD 5"),
					SiteInfo(name="Site B", plan="USD 10"),
					SiteInfo(name="Site Z", plan="USD 50"),
				],
				threads_per_worker=4,  # lesser workers since it has threads
			),
		],
		total_web_worker_slots=25,
		total_bg_worker_slots=8,
	)
	print("Guaranteed Worker Share:", scheduler.get_total_guaranteed_worker_share())
	print(scheduler.allocate_workers())
