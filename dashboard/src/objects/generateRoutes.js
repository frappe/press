import objects from './index.js'

export default function generateRoutes() {
	let routes = []
	for (let objectType in objects) {
		let object = objects[objectType]
		if (object.list) {
			let routeName = `${object.doctype} List`
			object.list.routeName = routeName
			routes.push({
				name: routeName,
				path: object.list.route,
				component:
					object.list.component || (() => import('../pages/ListPage.vue')),
				props: (route) => {
					return { objectType, ...route.params }
				},
			})
		}
		if (object.detail) {
			let children = object.detail.tabs.map((tab) => {
				const routeName = `${object.doctype} Detail ${tab.label}`
				tab.routeName = routeName
				const nestedChildren = []

				// nested children shouldn't be added to the main children array
				for (let route of tab.nestedChildrenRoutes || []) {
					nestedChildren.push({
						...route,
						props: (route) => {
							return { objectType, ...route.params }
						},
					})
				}

				return {
					name: routeName,
					path: tab.route,
					component: () => import('../pages/DetailTab.vue'),
					props: (route) => {
						return { ...route.params }
					},
					// Carries the query across, so a shared link with filters on it survives
					// the hop from the tab to its first child
					redirect: nestedChildren.length
						? (to) => ({
								name: tab.redirectTo,
								params: to.params,
								query: to.query,
							})
						: null,
					children: nestedChildren,
				}
			})
			if (object.routes) {
				for (let route of object.routes) {
					const staticProps = typeof route.props === 'object' ? route.props : {}

					children.push({
						...route,
						props: (route) => {
							return { objectType, ...route.params, ...staticProps }
						},
					})
				}
			}

			object.detail.routeName = `${object.doctype} Detail`
			routes.push({
				name: object.detail.routeName,
				path: object.detail.route,
				component: () => import('../pages/DetailPage.vue'),
				props: (route) => {
					return { objectType, ...route.params }
				},
				redirect: children.length ? { name: children[0].name } : null,
				children,
			})
		}
	}
	return routes
}
