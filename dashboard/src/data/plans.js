import { createResource } from 'frappe-ui'

import { teamCache } from '@/data/currentTeam'
export let plans = createResource({
	url: 'press.api.site.get_site_plans',
	cache: teamCache('site.plans'),
	initialData: [],
})

export function fetchPlans() {
	plans.fetch()
}

/**
 * Get plans
 * @returns {Array} List of plans
 */
export function getPlans() {
	return plans.data || []
}

export function getPlan(planName) {
	return getPlans().find((plan) => plan.name === planName)
}
