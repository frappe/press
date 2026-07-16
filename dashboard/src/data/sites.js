import { createListResource } from 'frappe-ui'

let sites

export function getActiveSites() {
	if (!sites) {
		sites = createListResource({
			doctype: 'Site',
			fields: ['name', 'host_name', 'status'],
			pageLength: 5,
			auto: false,
			cache: 'active-sites',
		})
	}
	return sites
}
