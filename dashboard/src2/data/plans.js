import { createResource } from 'frappe-ui';

let lastRefreshed = null;

export let plans = createResource({
	url: 'press.api.site.get_plans',
	cache: 'site.plans',
	initialData: [],
	onSuccess() {
		lastRefreshed = new Date();
	}
});

export function getPlans() {
	if (plans.data.length === 0) {
		plans.fetch();
	}
	// refresh if data is older than 10 seconds
	if (!lastRefreshed || new Date() - lastRefreshed > 10000) {
		plans.reload();
	}
	return plans.data || [];
}

export function getPlan(planName) {
	return getPlans().find(plan => plan.name === planName);
}
