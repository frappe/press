import { createListResource } from 'frappe-ui'

import { teamCache } from '@/data/currentTeam'

let sites

export function getActiveSites() {
	if (!sites) {
		sites = createListResource({
			doctype: 'Site',
			fields: [
				'name',
				'host_name',
				'status',
				'trial_end_date',
				'setup_wizard_complete',
				'additional_system_user_created',
				'standby_for_product',
				'group.version as version',
				'plan.plan_title as plan_title',
				'plan.price_usd as price_usd',
				'plan.price_inr as price_inr',
			],
			pageLength: 3,
			auto: false,
			cache: teamCache('active-sites'),
		})
	}
	return sites
}
