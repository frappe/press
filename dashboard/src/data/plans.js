import { createResource } from 'frappe-ui';

export let plans = createResource({
	url: 'press.api.site.get_site_plans',
	cache: 'site.plans',
	initialData: [],
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
	return getPlans().find((plan) => plan.name === planName);
}
