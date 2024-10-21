import Tooltip from 'frappe-ui/src/components/Tooltip/Tooltip.vue';
import LucideAppWindow from '~icons/lucide/app-window';
import type { VNode } from 'vue';
import { defineAsyncComponent, h } from 'vue';
import { getTeam, switchToTeam } from '../data/team';
import { icon } from '../utils/components';
import {
	clusterOptions,
	getSitesTabColumns,
	sitesTabRoute,
	siteTabFilterControls
} from './common';
import { getAppsTab } from './common/apps';
import { getJobsTab } from './common/jobs';
import type {
	Breadcrumb,
	BreadcrumbArgs,
	ColumnField,
	DashboardObject,
	Detail,
	FilterField,
	List,
	RouteDetail,
	Row,
	Tab
} from './common/types';
import { getLogsTab } from './tabs/site/logs';
import { getPatchesTab } from './common/patches';

export default {
	doctype: 'Bench',
	whitelistedMethods: {},
	detail: getDetail(),
	list: getList(),
	routes: getRoutes()
} satisfies DashboardObject as DashboardObject;

function getDetail() {
	return {
		titleField: 'name',
		statusBadge: ({ documentResource: bench }) => ({ label: bench.doc.status }),
		route: '/benches/:name',
		tabs: getTabs(),
		actions: ({ documentResource: res }) => {
			const team = getTeam();
			return [
				{
					label: 'Options',
					condition: () => team.doc?.is_desk_user ?? false,
					options: [
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							condition: () => team.doc?.is_desk_user,
							onClick() {
								window.open(
									`${window.location.protocol}//${window.location.host}/app/bench/${res.name}`,
									'_blank'
								);
							}
						},
						{
							label: 'Impersonate Team',
							icon: defineAsyncComponent(
								() => import('~icons/lucide/venetian-mask')
							),
							condition: () => window.is_system_user ?? false,
							onClick() {
								switchToTeam(res.doc.team);
							}
						}
					]
				}
			];
		}
		// breadcrumbs // use default breadcrumbs
	} satisfies Detail as Detail;
}

function getTabs() {
	return [
		getSitesTab(),
		getAppsTab(false),
		getJobsTab('Bench'),
		getProcessesTab(),
		getLogsTab(false),
		getPatchesTab(true)
	] satisfies Tab[] as Tab[];
}

function getRoutes() {
	return [
		{
			name: 'Bench Job',
			path: 'jobs/:id',
			component: () => import('../pages/JobPage.vue')
		},
		{
			name: 'Bench Log',
			path: 'logs/:logName',
			component: () => import('../pages/LogPage.vue')
		}
	] satisfies RouteDetail[] as RouteDetail[];
}

function getList() {
	return {
		route: '/benches',
		title: 'Benches',
		fields: [
			'group.title as group_title',
			'cluster.name as cluster_name',
			'cluster.image as cluster_image',
			'cluster.title as cluster_title'
		],
		orderBy: 'creation desc',
		searchField: 'name',
		columns: [
			{
				label: 'Bench',
				fieldname: 'name',
				width: 1.5,
				class: 'font-medium',
				suffix: getBenchTitleSuffix
			},
			{ label: 'Status', fieldname: 'status', type: 'Badge', width: 0.6 },
			{ label: 'Sites', fieldname: 'site_count', type: 'Number' },
			{
				label: 'Region',
				fieldname: 'cluster',
				width: 1,
				format: (value, row) => String(row.cluster_title || value || ''),
				prefix: getClusterImagePrefix
			},
			{ label: 'Bench Group', fieldname: 'group_title' }
		],
		filterControls
	} satisfies List as List;
}

function getBenchTitleSuffix(row: Row) {
	const ch: VNode[] = [];
	if (row.inplace_update_docker_image) ch.push(getInPlaceUpdatesSuffix(row));
	if (row.has_app_patch_applied) ch.push(getAppPatchSuffix(row));
	if (!ch.length) return;

	return h(
		'div',
		{
			class: 'flex flex-row gap-2'
		},
		ch
	);
}

function getInPlaceUpdatesSuffix(row: Row) {
	const count = Number(
		String(row.inplace_update_docker_image).split('-').at(-1)
	);

	let title = 'Bench has been updated in place';
	if (!Number.isNaN(count) && count > 1) {
		title += ` ${count} times`;
	}

	return h(
		'div',
		{
			title,
			class: 'rounded-full bg-gray-100 p-1'
		},
		h(icon('star', 'w-3 h-3'))
	);
}

function getAppPatchSuffix(row: Row) {
	return h(
		'div',
		{
			title: 'Apps in this bench may have been patched',
			class: 'rounded-full bg-gray-100 p-1'
		},
		h(icon('hash', 'w-3 h-3'))
	);
}

function getClusterImagePrefix(row: Row) {
	if (!row.cluster_image) return;

	return h('img', {
		src: row.cluster_image,
		class: 'w-4 h-4',
		alt: row.cluster_title
	});
}

function filterControls() {
	return [
		{
			type: 'select',
			label: 'Status',
			fieldname: 'status',
			options: [
				'',
				'Active',
				'Pending',
				'Installing',
				'Updating',
				'Broken',
				'Archived'
			]
		},
		{
			type: 'link',
			label: 'Bench Group',
			fieldname: 'group',
			options: {
				doctype: 'Release Group'
			}
		},
		{
			type: 'select',
			label: 'Region',
			fieldname: 'cluster',
			options: clusterOptions
		}
	] satisfies FilterField[] as FilterField[];
}

export function getSitesTab() {
	return {
		label: 'Sites',
		icon: icon(LucideAppWindow),
		route: 'sites',
		type: 'list',
		list: {
			doctype: 'Site',
			filters: r => ({
				group: r.doc.group,
				bench: r.name,
				skip_team_filter_for_system_user_and_support_agent: true
			}),
			fields: [
				'name',
				'status',
				'host_name',
				'plan.plan_title as plan_title',
				'plan.price_usd as price_usd',
				'plan.price_inr as price_inr',
				'cluster.image as cluster_image',
				'cluster.title as cluster_title'
			],
			orderBy: 'creation desc, bench desc',
			pageLength: 99999,
			columns: getSitesTabColumns(true),
			filterControls: siteTabFilterControls,
			route: sitesTabRoute,
			primaryAction: r => {
				return {
					label: 'New Site',
					slots: {
						prefix: icon('plus', 'w-4 h-4')
					},
					route: {
						name: 'Release Group New Site',
						params: { bench: r.documentResource.doc.group }
					}
				};
			},
			rowActions: ({ row }) => [
				{
					label: 'View in Desk',
					condition: () => getTeam()?.doc?.is_desk_user,
					onClick() {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/site/${row.name}`,
							'_blank'
						);
					}
				}
			]
		}
	} satisfies Tab;
}

export function getProcessesTab() {
	const url = 'press.api.bench.get_processes';
	return {
		label: 'Processes',
		icon: icon('cpu'),
		route: 'processes',
		type: 'list',
		list: {
			resource({ documentResource: res }) {
				return {
					params: {
						name: res.name
					},
					url,
					auto: true,
					cache: ['ObjectList', url, res.name]
				};
			},
			columns: getProcessesColumns(),
			rowActions: () => [] // TODO: allow issuing supectl commands
		}
	} satisfies Tab as Tab;
}

export function getProcessesColumns() {
	const processStatusColorMap = {
		Starting: 'blue',
		Backoff: 'yellow',
		Running: 'green',
		Stopping: 'yellow',
		Stopped: 'gray',
		Exited: 'gray',
		Unknown: 'gray',
		Fatal: 'red'
	};

	type Status = keyof typeof processStatusColorMap;
	return [
		{
			label: 'Name',
			width: 2,
			fieldname: 'name'
		},
		{
			label: 'Group',
			width: 1.5,
			fieldname: 'group',
			format: v => String(v ?? '')
		},
		{
			label: 'Status',
			type: 'Badge',
			width: 0.7,
			fieldname: 'status',
			theme: value => processStatusColorMap[value as Status] ?? 'gray',
			suffix: ({ message }) => {
				if (!message) {
					return;
				}

				return h(
					Tooltip,
					{
						text: message,
						placement: 'top'
					},
					() => h(icon('alert-circle', 'w-3 h-3'))
				);
			}
		},
		{
			label: 'Uptime',
			fieldname: 'uptime_string'
		}
	] satisfies ColumnField[] as ColumnField[];
}

function breadcrumbs({ items, documentResource: bench }: BreadcrumbArgs) {
	const $team = getTeam();
	const benchCrumb = {
		label: bench.doc?.name,
		route: `/benches/${bench.doc?.name}`
	};

	if (bench.doc.group_team == $team.doc?.name || $team.doc?.is_desk_user) {
		return [
			{
				label: bench.doc?.group_title,
				route: `/groups/${bench.doc?.group}`
			},
			benchCrumb
		] satisfies Breadcrumb[];
	}

	return [...items.slice(0, -1), benchCrumb] satisfies Breadcrumb[];
}
