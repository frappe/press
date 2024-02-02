import { createResource } from 'frappe-ui';

export let plans = createResource({
	url: 'press.api.site.get_plans',
	cache: 'site.plans'
});
plans.fetch();

export function getPlan(planName) {
	return (plans.data || []).find(plan => plan.name === planName);
}
