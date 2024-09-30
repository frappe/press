interface DashboardObject {
	doctype: string;
	detail: {
		titleField: string;
		statusBadge: () => {};
		breadcrumbs: () => {};
		route: string;
		tabs: object[];
		actions: () => {};
	};
}
