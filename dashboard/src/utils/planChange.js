import { getTeam } from '../data/team'
import { bytes, plural, userCurrency } from './format'

// A plan name says nothing about what the plan gives you, so the plan history
// lists show the price and the resources instead. `get_list_query` on Plan
// Change and Site Plan Change puts the two plans on the row for that.
export function planChange(row, describe) {
	const toPlan = row?.to_plan_details
	if (!toPlan) return '—'

	const fromPlan = row?.from_plan_details
	if (!fromPlan) return describe(toPlan)

	// A price change does not have to change the size, and the other way round.
	const before = describe(fromPlan)
	const after = describe(toPlan)
	if (before === after) return after

	return `${before} → ${after}`
}

export function planPrice(plan) {
	const $team = getTeam()
	const price = $team.doc?.currency === 'INR' ? plan.price_inr : plan.price_usd
	if (price > 0) return `${userCurrency(price, 0)}/mo`

	return plan.title || plan.plan_title || plan.name
}

export function serverPlanCpu(plan) {
	return String(plan.vcpu)
}

export function serverPlanMemory(plan) {
	return bytes(plan.memory, 0, 2)
}

// A site on a dedicated server has no share of a shared server to report, so
// its plan carries limits that stand in for no limit at all.
export function sitePlanCompute(plan) {
	if (plan.dedicated_server_plan) return 'Unlimited'

	const hours = plan.cpu_time_per_day
	return `${hours} ${plural(hours, 'hour', 'hours')}/day`
}

export function sitePlanStorage(plan) {
	if (plan.dedicated_server_plan) return 'Unlimited'

	return bytes(plan.max_storage_usage, 0, 2)
}
