import { createResource } from 'frappe-ui';

export let plans = createResource({
	url: 'press.api.site.get_plans',
	cache: 'site.plans'
});

plans.fetch();
