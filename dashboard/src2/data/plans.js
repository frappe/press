import { createResource } from 'frappe-ui';

let plansFetched = null;

export let plans = createResource({
	url: 'press.api.site.get_plans',
	cache: 'site.plans',
	initialData: [],
	onSuccess() {
		plansFetched = true;
	}
});

export function getPlans() {
	if (!plansFetched) {
		plans.fetch();
	}
	return plans.data || [];
}

export function getPlan(planName) {
	return getPlans().find(plan => plan.name === planName);
}
