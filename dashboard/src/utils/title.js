const APP_NAME = 'Frappe Cloud'

// Joins the parts of a page title, outermost first, and appends the app name.
// pageTitle('Bench One', 'Config') -> 'Bench One - Config - Frappe Cloud'
export function pageTitle(...parts) {
	return [...parts, APP_NAME].filter(Boolean).join(' - ')
}

// The title of a route, built from the meta.title of every record it matched.
export function routeTitle(route) {
	return pageTitle(...route.matched.map((record) => recordTitle(record, route)))
}

// The title of the innermost record, which is the tab a detail page sits on.
export function leafTitle(route) {
	return recordTitle(route.matched[route.matched.length - 1], route)
}

function recordTitle(record, route) {
	let title = record?.meta?.title
	return typeof title === 'function' ? title(route) : title
}
