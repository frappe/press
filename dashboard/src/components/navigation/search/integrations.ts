import { reactive, watch } from 'vue';
import { createListResource } from 'frappe-ui';

export const integrations = reactive({
	Sites: {
		icon: LucidePanelTopInactive,
		items: [],
	},

	Servers: {
		icon: LucideServer,
		items: [],
	},

	Benches: {
		icon: LucideBoxes,
		items: [],
	},
});

export const addIntegrations = () => {
	let siteList = createListResource({
		auto: true,
		doctype: 'Site',
		cache: ['ObjectList', 'Site'],
		fields: ['name', 'status'],
		pageLength: 10000,
		onSuccess(data) {
			const defaultItems = [
				{ name: 'List', route: '/sites', icon: LucideEarth },
				{ name: 'New', route: '/sites/new', icon: LucideCirclePlus },
			];

			const tmp = data.map((x) => {
				const route = `/sites/${x.name}/overview`;
				return { ...x, route, icon: LucideCircleDashed, spacer: true };
			});
			integrations.Sites.items = defaultItems.concat(tmp);
		},
	});

	let benches = createListResource({
		auto: true,
		doctype: 'Release Group',
		cache: ['ObjectList', 'Release Group'],
		fields: ['name', 'status', 'title', 'sites'],
		pageLength: 10000,
		onSuccess(data) {
			const defaultItems = [
				{ name: 'New', route: '/groups/new', icon: LucideBoxes },
			];
			const tmp = data.map((x) => {
				const route = `/groups/${x.name}/sites`;
				return { ...x, route, icon: LucideCircleDashed };
			});
			integrations.Benches.items = defaultItems.concat(tmp);
		},
	});

	let serverList = createListResource({
		auto: true,
		doctype: 'Server',
		cache: ['ObjectList', 'Server'],
		fields: ['name', 'status', 'title', 'sites'],
		pageLength: 10000,
		onSuccess(data) {
			const defaultItems = [
					{ name: 'List', route: '/servers', icon: LucideServer },
					{ name: 'New', route: '/servers/new', icon: LucideCirclePlus },
				],
				tmp = data.map((x) => {
					const route = `/servers/${x.name}/overview`;
					return { ...x, route, icon: LucideCircleDashed };
				});
			integrations.Servers.items = defaultItems.concat(tmp);
		},
	});
};
