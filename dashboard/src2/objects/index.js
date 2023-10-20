import site from './site';
import bench from './bench';

let objects = [site, bench];

export function generateRoutes() {
	let routes = [];
	for (let object of objects) {
		if (object.list) {
			routes.push({
				name: `${object.doctype} List`,
				path: object.list.route,
				component: () => import('../pages/ListPage.vue'),
				props: route => {
					return { object, ...route.params };
				}
			});
		}
		if (object.detail) {
			let children = object.detail.tabs.map(tab => {
				return {
					name: `${object.doctype} Detail ${tab.label}`,
					path: tab.route,
					component: () => import('../pages/DetailTab.vue'),
					props: route => {
						return { ...route.params };
					}
				};
			});
			routes.push({
				name: `${object.doctype} Detail`,
				path: object.detail.route,
				component: () => import('../pages/DetailPage.vue'),
				props: route => {
					return { object, ...route.params };
				},
				redirect: { name: children[0].name },
				children
			});
		}
	}
	return routes;
}

export default objects;
