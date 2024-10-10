import type { defineAsyncComponent, h, Component } from 'vue';
import type { icon } from '../utils/components';

type ListResource = unknown;
type Resource = unknown;

type Icon = ReturnType<typeof icon>;
type AsyncComponent = ReturnType<typeof defineAsyncComponent>;

export interface DashboardObject {
	doctype: string;
	whitelistedMethods: Record<string, string>;
	list: List;
	detail: {
		titleField: string;
		statusBadge: StatusBadge;
		breadcrumbs: Breadcrumbs;
		route: string;
		tabs: Tab[];
		actions: (r: { documentResource: Resource }) => Action[];
	};
	routes: RouteDetail[];
}

interface List {
	route: string;
	title: string;
	fields: string[]; // TODO: Incomplete
	searchField: string;
	columns: ColumnField[];
	filterControls: FilterControls;
	primaryAction: PrimaryAction;
}

type FilterControls = () => FilterField[];
type PrimaryAction = (r: { listResource: ListResource }) => {
	label: string;
	variant: string;
	slots: {
		prefix: Icon;
	};
	onClick: () => void;
};
type StatusBadge = (r: { documentResource: Resource }) => { label: string };
type Breadcrumbs = (r: { documentResource: Resource; items: unknown[] }) => {
	label: string;
	route: string;
};

interface FilterField {
	label: string;
	fieldname: string;
	type: string;
	options?: {
		doctype: string;
		filters?: {
			doctype_name?: string;
		};
	};
}

interface ColumnField {
	label: string;
	fieldname: string;
	class?: string;
	width?: string | number;
	format?: (value: unknown, row: unknown) => string;
	link?: (value: unknown, row: unknown) => string;
	suffix?: (row: unknown) => ReturnType<typeof h>;
}

interface Tab {
	label: string;
	icon: Icon;
	route: string;
	type: string;
	childrenRoutes?: string[];
	component?: AsyncComponent;
	props?: (r: Resource) => Record<string, unknown>;
	list?: TabList;
}

interface TabList {
	doctype: string;
	filters: (r: Resource) => Record<string, unknown>;
	route?: (row: unknown) => Route;
	pageLength: number;
	columns: ColumnField[];
	orderBy: string;
	rowActions: (r: {
		row: unknown;
		listResource: ListResource;
		documentResource: Resource;
	}) => Action[];
	primaryAction: (r: {
		listResource: ListResource;
		documentResource: Resource;
	}) => {
		label: string;
		slots: {
			prefix: Icon;
		};
		onClick: () => void;
		variant?: string;
	};
	filterControls?: () => FilterField[];
	fields: Record<string, string[]>[];
	banner: (r: {
		documentResource: Resource;
	}) => { title: string; type: string } | null;
	experimental?: boolean;
	documentation?: string;
}

interface Action {
	label: string;
	slots?: {
		prefix?: Icon;
	};
	theme?: string;
	variant?: string;
	onClick: () => void;
	condition?: () => boolean;
	route?: Route;
	options?: Option[];
}

interface Route {
	name: string;
	params: unknown;
}

interface RouteDetail {
	name: string;
	path: string;
	component: Component;
}

interface Option {
	label: string;
	icon: Icon | AsyncComponent;
	condition: () => boolean;
	onClick: () => void;
}
