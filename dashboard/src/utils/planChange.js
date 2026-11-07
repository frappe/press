import { h } from 'vue'
import { getTeam } from '../data/team'
import { bytes, plural, userCurrency } from './format'

// A plan name says nothing about what the plan gives you, so the plan history
// lists show the price and the resources instead. `get_list_query` on Plan
// Change and Site Plan Change puts the two plans on the row for that.
//
// Both values keep the ink of the row. Only the arrow between them is dimmed,
// so it separates the two values without competing with them.
export function planChangeCell(describe) {
	return ({ row }) => {
		const toPlan = row?.to_plan_details
		if (!toPlan) return value('—')

		const fromPlan = row?.from_plan_details
		const after = describe(toPlan)
		if (!fromPlan) return value(after)

		// A price change does not have to change the size, and the other way round.
		const before = describe(fromPlan)
		if (before === after) return value(after)

		return h('div', { class: 'flex items-center gap-1.5 truncate text-base' }, [
			value(before),
			h('span', { class: 'shrink-0 text-ink-gray-4' }, '→'),
			value(after),
		])
	}
}

function value(text) {
	return h('span', { class: 'truncate text-base' }, text)
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
