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

/**
 * Check if a plan is available on a cloud provider
 * @param {Object} plan
 * @param {String} provider
 * @returns {Boolean}
 */
export function planSupportsProvider(plan, provider) {
	if (!plan.cloud_providers?.length) return true;
	if (['Generic', 'Scaleway'].includes(provider)) provider = 'AWS EC2';
	return plan.cloud_providers.includes(provider);
}

/**
 * Get the cheapest public plan that allows a site on a private bench
 * @param {String} provider
 * @returns {Object|undefined}
 */
export function getCheapestPrivateBenchPlan(provider) {
	return getPlans()
		.filter(
			(plan) =>
				plan.private_benches &&
				plan.price_usd > 0 &&
				!plan.dedicated_server_plan &&
				!plan.restricted_plan &&
				planSupportsProvider(plan, provider),
		)
		.sort((a, b) => a.price_usd - b.price_usd)[0];
}
