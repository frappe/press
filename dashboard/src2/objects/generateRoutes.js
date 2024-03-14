import objects from './index.js';

export default function generateRoutes() {
	let routes = [];
	for (let objectType in objects) {
		let object = objects[objectType];
		if (object.list) {
			let routeName = `${object.doctype} List`;
			object.list.routeName = routeName;
			routes.push({
				name: routeName,
				path: object.list.route,
				component: () => import('../pages/ListPage.vue'),
				props: route => {
					return { objectType, ...route.params };
				}
			});
		}
		if (object.detail) {
			let children = object.detail.tabs.map(tab => {
				let routeName = `${object.doctype} Detail ${tab.label}`;
				tab.routeName = routeName;
				return {
					name: routeName,
					path: tab.route,
					component: () => import('../pages/DetailTab.vue'),
					props: route => {
						return { ...route.params };
					}
				};
			});
			if (object.routes) {
				for (let route of object.routes) {
					children.push({
						...route,
						props: route => {
							return { objectType, ...route.params };
						}
					});
				}
			}

			object.detail.routeName = `${object.doctype} Detail`;
			routes.push({
				name: object.detail.routeName,
				path: object.detail.route,
				component: () => import('../pages/DetailPage.vue'),
				props: route => {
					return { objectType, ...route.params };
				},
				redirect: children.length ? { name: children[0].name } : null,
				children
			});
		}
	}
	return routes;
}
