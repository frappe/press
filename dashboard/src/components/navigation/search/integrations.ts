import { reactive, watch } from 'vue';
import { createListResource } from 'frappe-ui';

export const integrations = reactive({
	Sites: {
		icon: LucidePanelTopInactive,
		items: [],
	},

	Serveurs: {
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
				{ name: 'Liste', route: '/sites', icon: LucideCircleDashed },
				{ name: 'Nouveau', route: '/sites/new', icon: LucideCirclePlus },
			];

			const tmp = data.map((x) => {
				const route = `/sites/${x.name}/overview`;
				return { ...x, route, icon: LucideEarth };
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
				{ name: 'Nouveau', route: '/groups/new', icon: LucideCirclePlus },
			];
			const tmp = data.map((x) => {
				const route = `/groups/${x.name}/sites`;
				return { ...x, route, icon: LucideBoxes };
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
				{ name: 'Liste', route: '/servers', icon: LucideCircleDashed },
				{ name: 'Nouveau', route: '/servers/new', icon: LucideCirclePlus },
			];
			const tmp = data.map((x) => {
				const route = `/servers/${x.name}/overview`;
				return { ...x, route, icon: LucideServer };
			});
			integrations.Serveurs.items = defaultItems.concat(tmp);
		},
	});
};
