import type { defineAsyncComponent, h, Component } from 'vue';
import type { icon } from '../../utils/components';

type ListResource = {
	data: Record<string, unknown>[];
	reload: () => void;
	runDocMethod: {
		submit: (r: { method: string; [key: string]: any }) => Promise<unknown>;
	};
	delete: {
		submit: (name: string, cb: { onSuccess: () => void }) => Promise<unknown>;
	};
};
export interface ResourceBase {
	url: string;
	auto: boolean;
	cache: string[];
}

export interface ResourceWithParams extends ResourceBase {
	params: Record<string, unknown>;
}

export interface ResourceWithMakeParams extends ResourceBase {
	makeParams: () => Record<string, unknown>;
}

export type Resource = ResourceWithParams | ResourceWithMakeParams;

export interface DocumentResource {
	name: string;
	doc: Record<string, any>;
	[key: string]: any;
}

type Icon = ReturnType<typeof icon>;
type AsyncComponent = ReturnType<typeof defineAsyncComponent>;

export interface DashboardObject {
	doctype: string;
	whitelistedMethods: Record<string, string>;
	list: List;
	detail: Detail;
	routes: RouteDetail[];
}

export interface Detail {
	titleField: string;
	statusBadge: StatusBadge;
	breadcrumbs?: Breadcrumbs;
	route: string;
	tabs: Tab[];
	actions: (r: { documentResource: DocumentResource }) => Action[];
}

export interface List {
	route: string;
	title: string;
	fields: string[]; // TODO: Incomplete
	searchField: string;
	columns: ColumnField[];
	orderBy: string;
	filterControls: FilterControls;
	primaryAction?: PrimaryAction;
}
type R = {
	listResource: ListResource;
	documentResource: DocumentResource;
};
type FilterControls = (r: R) => FilterField[];
type PrimaryAction = (r: R) => {
	label: string;
	variant?: string;
	slots: {
		prefix: Icon;
	};
	onClick?: () => void;
};
type StatusBadge = (r: { documentResource: DocumentResource }) => {
	label: string;
};
export type Breadcrumb = { label: string; route: string };
export type BreadcrumbArgs = {
	documentResource: DocumentResource;
	items: Breadcrumb[];
};
export type Breadcrumbs = (r: BreadcrumbArgs) => Breadcrumb[];

export interface FilterField {
	label: string;
	fieldname: string;
	type: string;
	class?: string;
	options?:
		| {
				doctype: string;
				filters?: {
					doctype_name?: string;
				};
		  }
		| string[];
}

export interface ColumnField {
	label: string;
	fieldname?: string;
	class?: string;
	width?: string | number;
	type?: string;
	format?: (value: any, row: Row) => string | undefined;
	link?: (value: unknown, row: Row) => string;
	prefix?: (row: Row) => Component | undefined;
	suffix?: (row: Row) => Component | undefined;
	theme?: (value: unknown) => string;
	align?: 'left' | 'right';
}

export type Row = Record<string, any>;

export interface Tab {
	label: string;
	icon: Icon;
	route: string;
	type: string;
	condition?: (r: DocumentResource) => boolean;
	childrenRoutes?: string[];
	component?: AsyncComponent;
	props?: (r: DocumentResource) => Record<string, unknown>;
	list?: TabList;
}

export interface TabList {
	doctype?: string;
	orderBy?: string;
	filters?: (r: DocumentResource) => Record<string, unknown>;
	route?: (row: Row) => Route;
	pageLength?: number;
	columns: ColumnField[];
	fields?: Record<string, string[]>[] | string[];
	rowActions?: (r: {
		row: Row;
		listResource: ListResource;
		documentResource: DocumentResource;
	}) => Action[];
	primaryAction?: PrimaryAction;
	filterControls?: FilterControls;
	banner?: (r: {
		documentResource: DocumentResource;
	}) => BannerConfig | undefined;
	searchField?: string;
	experimental?: boolean;
	documentation?: string;
	resource?: (r: { documentResource: DocumentResource }) => Resource;
}

interface Action {
	label: string;
	slots?: {
		prefix?: Icon;
	};
	theme?: string;
	variant?: string;
	onClick?: () => void;
	condition?: () => boolean;
	route?: Route;
	options?: Option[];
}

export interface Route {
	name: string;
	params: Record<string, unknown>;
}

export interface RouteDetail {
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

export interface BannerConfig {
	title: string;
	dismissable: boolean;
	id: string;
	type?: string;
	button?: {
		label: string;
		variant: string;
		onClick?: () => void;
	};
}

export interface DialogConfig {
	title: string;
	message: string;
	primaryAction?: { onClick: () => void };
	onSuccess?: (o: { hide: () => void }) => void;
}

export interface Process {
	program: string;
	name: string;
	status: string;
	uptime?: number;
	uptime_string?: string;
	message?: string;
	group?: string;
	pid?: number;
}
