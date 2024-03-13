import { createResource } from 'frappe-ui';

export let plans = createResource({
	url: 'press.api.site.get_plans',
	cache: 'site.plans'
});

export function getPlan(planName) {
	if (!plans.data) plans.fetch();
	return (plans.data || []).find(plan => plan.name === planName);
}
