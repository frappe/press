import { createResource } from 'frappe-ui';

export let plans = createResource({
	url: 'press.saas.api.site.get_plans',
	cache: 'site.saas_plans',
	initialData: []
});

export function fetchPlans() {
	plans.fetch();
}

/**
 * Get plans
 * @returns {Array} List of plans
 */
export function getPlans() {
	return plans.data || [];
}

export function getPlan(planName) {
	return getPlans().find(plan => plan.name === planName);
}
